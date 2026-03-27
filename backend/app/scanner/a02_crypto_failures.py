import asyncio
import re
import ssl
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class CryptographicFailuresScanner(BaseScannerModule):
    category = "A02"
    name = "Cryptographic Failures"
    description = "Checks TLS configuration, certificate validity, mixed content, HSTS, and sensitive data exposure."

    WEAK_PROTOCOLS = {
        ssl.TLSVersion.TLSv1: "TLS 1.0",
        ssl.TLSVersion.TLSv1_1: "TLS 1.1",
    }

    SENSITIVE_URL_PATTERNS = [
        r"password=", r"passwd=", r"token=", r"api_key=", r"apikey=",
        r"secret=", r"access_token=", r"auth=", r"session_id=",
    ]

    async def scan(self) -> list[FindingData]:
        parsed = urlparse(self.target_url)
        is_https = parsed.scheme == "https"
        host = parsed.hostname or ""
        port = parsed.port or (443 if is_https else 80)

        coros = [
            self._check_https_redirect(is_https),
            self._check_hsts(),
            self._check_mixed_content(is_https),
            self._check_sensitive_data_in_urls(),
        ]
        if is_https:
            coros.append(self._check_tls_certificate(host, port))
        results = await asyncio.gather(*coros)
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_https_redirect(self, is_https: bool) -> list[FindingData]:
        if is_https:
            return []
        # Check if the site is only available over HTTP
        return [self._finding(
            severity=Severity.HIGH,
            title="Site Not Using HTTPS",
            description="The target URL uses HTTP instead of HTTPS. All data transmitted between the user and server is unencrypted, making it vulnerable to eavesdropping and man-in-the-middle attacks.",
            remediation="Enable HTTPS by obtaining a TLS certificate (e.g., from Let's Encrypt) and configuring your web server to redirect all HTTP traffic to HTTPS.",
            confidence=Confidence.HIGH,
        )]

    async def _check_tls_certificate(self, host: str, port: int) -> list[FindingData]:
        findings = []
        try:
            ctx = ssl.create_default_context()
            # Allow connection even with invalid certs for inspection
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            loop = asyncio.get_event_loop()
            cert_info = await loop.run_in_executor(
                None, self._get_cert_info, host, port
            )

            if cert_info is None:
                return findings

            # Check expiry
            not_after = cert_info.get("notAfter")
            if not_after:
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if expiry < now:
                    findings.append(self._finding(
                        severity=Severity.CRITICAL,
                        title="TLS Certificate Expired",
                        description=f"The TLS certificate expired on {not_after}. Browsers will show security warnings and users' connections are not properly secured.",
                        remediation="Renew the TLS certificate immediately. Consider using automated renewal with Let's Encrypt/certbot.",
                        evidence=f"Certificate expiry: {not_after}",
                        confidence=Confidence.HIGH,
                    ))
                elif (expiry - now).days < 30:
                    findings.append(self._finding(
                        severity=Severity.LOW,
                        title="TLS Certificate Expiring Soon",
                        description=f"The TLS certificate expires on {not_after}, which is less than 30 days away.",
                        remediation="Renew the TLS certificate before it expires. Set up automated renewal.",
                        evidence=f"Certificate expiry: {not_after}, Days remaining: {(expiry - now).days}",
                        confidence=Confidence.HIGH,
                    ))

            # Check self-signed
            issuer = cert_info.get("issuer", ())
            subject = cert_info.get("subject", ())
            if issuer == subject:
                findings.append(self._finding(
                    severity=Severity.HIGH,
                    title="Self-Signed TLS Certificate",
                    description="The TLS certificate appears to be self-signed. Browsers will show security warnings and the identity of the server cannot be verified.",
                    remediation="Obtain a certificate from a trusted Certificate Authority (CA) such as Let's Encrypt.",
                    evidence=f"Issuer and Subject match: {issuer}",
                    confidence=Confidence.HIGH,
                ))

        except Exception:
            pass

        return findings

    def _get_cert_info(self, host: str, port: int) -> dict | None:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    return ssock.getpeercert(binary_form=False) or None
        except Exception:
            return None

    async def _check_hsts(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        hsts = resp.headers.get("strict-transport-security", "")
        if not hsts:
            return [self._finding(
                severity=Severity.MEDIUM,
                title="Missing HTTP Strict Transport Security (HSTS) Header",
                description="The server does not send the Strict-Transport-Security header. Without HSTS, browsers may still attempt insecure HTTP connections, making users vulnerable to downgrade attacks.",
                remediation="Add the header: Strict-Transport-Security: max-age=31536000; includeSubDomains",
                evidence=f"Response headers do not include Strict-Transport-Security",
                confidence=Confidence.HIGH,
            )]

        # Check max-age value
        match = re.search(r"max-age=(\d+)", hsts)
        if match and int(match.group(1)) < 31536000:
            return [self._finding(
                severity=Severity.LOW,
                title="HSTS max-age Too Short",
                description=f"The HSTS max-age is set to {match.group(1)} seconds, which is less than the recommended 1 year (31536000 seconds).",
                remediation="Increase HSTS max-age to at least 31536000 (1 year): Strict-Transport-Security: max-age=31536000; includeSubDomains",
                evidence=f"HSTS header: {hsts}",
                confidence=Confidence.HIGH,
            )]

        return []

    async def _check_mixed_content(self, is_https: bool) -> list[FindingData]:
        if not is_https:
            return []

        resp = await self._get()
        if resp is None:
            return []

        # Look for http:// resources in HTML
        http_resources = re.findall(r'(?:src|href|action)=["\']http://[^"\']+["\']', resp.text, re.IGNORECASE)
        if http_resources:
            return [self._finding(
                severity=Severity.MEDIUM,
                title="Mixed Content Detected",
                description=f"The HTTPS page loads {len(http_resources)} resource(s) over insecure HTTP. This undermines the security of HTTPS and may trigger browser warnings.",
                remediation="Update all resource URLs to use HTTPS or protocol-relative URLs (//). Use Content-Security-Policy: upgrade-insecure-requests as a migration aid.",
                evidence="\n".join(http_resources[:5]),
                confidence=Confidence.HIGH,
            )]

        return []

    async def _check_sensitive_data_in_urls(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        # Check all URLs in the page
        urls = re.findall(r'(?:href|src|action)=["\']([^"\']+)["\']', resp.text)
        for url in urls:
            for pattern in self.SENSITIVE_URL_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    findings.append(self._finding(
                        severity=Severity.HIGH,
                        title="Sensitive Data Exposed in URL",
                        description=f"A URL on the page contains what appears to be sensitive data (matches pattern '{pattern}'). URL parameters are logged in browser history, server logs, and referrer headers.",
                        remediation="Never pass sensitive data in URL query parameters. Use POST request bodies or HTTP headers instead.",
                        evidence=url[:200],
                        confidence=Confidence.MEDIUM,
                    ))
                    break

        return findings[:3]  # Limit to 3 findings
