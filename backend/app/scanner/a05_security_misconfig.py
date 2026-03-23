import asyncio

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class SecurityMisconfigScanner(BaseScannerModule):
    category = "A05"
    name = "Security Misconfiguration"
    description = "Audits security headers, exposed files, CORS configuration, cookie flags, and server info disclosure."

    REQUIRED_HEADERS = {
        "content-security-policy": {
            "severity": Severity.MEDIUM,
            "title": "Missing Content-Security-Policy Header",
            "desc": "No Content-Security-Policy (CSP) header is set. CSP helps prevent XSS attacks by controlling which resources the browser is allowed to load.",
            "fix": "Add a Content-Security-Policy header. Start with: Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
        },
        "x-content-type-options": {
            "severity": Severity.LOW,
            "title": "Missing X-Content-Type-Options Header",
            "desc": "The X-Content-Type-Options header is not set to 'nosniff'. Browsers may MIME-sniff responses, potentially treating non-executable MIME types as executable.",
            "fix": "Add the header: X-Content-Type-Options: nosniff",
        },
        "x-frame-options": {
            "severity": Severity.MEDIUM,
            "title": "Missing X-Frame-Options Header",
            "desc": "The X-Frame-Options header is missing. The page can be embedded in iframes on other sites, enabling clickjacking attacks.",
            "fix": "Add the header: X-Frame-Options: DENY (or SAMEORIGIN if framing from same origin is needed). Alternatively, use CSP frame-ancestors directive.",
        },
        "referrer-policy": {
            "severity": Severity.LOW,
            "title": "Missing Referrer-Policy Header",
            "desc": "No Referrer-Policy header is set. The browser may leak the full URL (including query parameters) to third-party sites via the Referer header.",
            "fix": "Add the header: Referrer-Policy: strict-origin-when-cross-origin",
        },
        "permissions-policy": {
            "severity": Severity.LOW,
            "title": "Missing Permissions-Policy Header",
            "desc": "No Permissions-Policy (formerly Feature-Policy) header is set. Browser features like camera, microphone, and geolocation are not restricted.",
            "fix": "Add the header: Permissions-Policy: camera=(), microphone=(), geolocation=()",
        },
    }

    EXPOSED_FILES = [
        ("/.env", "Environment configuration file"),
        ("/.git/HEAD", "Git repository metadata"),
        ("/wp-config.php", "WordPress configuration"),
        ("/phpinfo.php", "PHP information page"),
        ("/server-status", "Apache server status"),
        ("/web.config", "IIS configuration"),
        ("/.htaccess", "Apache configuration"),
        ("/composer.json", "PHP dependency manifest"),
        ("/package.json", "Node.js dependency manifest"),
        ("/.DS_Store", "macOS directory metadata"),
        ("/config.yml", "YAML configuration"),
        ("/config.yaml", "YAML configuration"),
        ("/database.yml", "Database configuration"),
        ("/.dockerenv", "Docker environment marker"),
        ("/Dockerfile", "Docker build file"),
    ]

    async def scan(self) -> list[FindingData]:
        results = await asyncio.gather(
            self._check_security_headers(),
            self._check_server_disclosure(),
            self._check_exposed_files(),
            self._check_cors(),
            self._check_cookie_flags(),
        )
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_security_headers(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}

        for header, info in self.REQUIRED_HEADERS.items():
            if header not in headers_lower:
                # Check if CSP is covered by frame-ancestors (for x-frame-options)
                if header == "x-frame-options" and "content-security-policy" in headers_lower:
                    csp = headers_lower["content-security-policy"]
                    if "frame-ancestors" in csp:
                        continue

                findings.append(self._finding(
                    severity=info["severity"],
                    title=info["title"],
                    description=info["desc"],
                    remediation=info["fix"],
                    evidence=f"Header '{header}' not found in response headers.",
                    confidence=Confidence.HIGH,
                ))

        # Check X-Content-Type-Options value
        xcto = headers_lower.get("x-content-type-options", "")
        if xcto and xcto.lower() != "nosniff":
            findings.append(self._finding(
                severity=Severity.LOW,
                title="X-Content-Type-Options Not Set to 'nosniff'",
                description=f"The X-Content-Type-Options header is set to '{xcto}' instead of 'nosniff'.",
                remediation="Set the header value to: nosniff",
                evidence=f"Current value: {xcto}",
                confidence=Confidence.HIGH,
            ))

        return findings

    async def _check_server_disclosure(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}

        # Check Server header for version
        server = headers_lower.get("server", "")
        if server and any(c.isdigit() for c in server):
            findings.append(self._finding(
                severity=Severity.LOW,
                title="Server Version Disclosed in Headers",
                description=f"The Server header reveals version information: '{server}'. This helps attackers identify specific software versions with known vulnerabilities.",
                remediation="Configure the web server to suppress version information. For Apache: ServerTokens Prod. For Nginx: server_tokens off.",
                evidence=f"Server: {server}",
                confidence=Confidence.HIGH,
            ))

        # Check X-Powered-By
        powered_by = headers_lower.get("x-powered-by", "")
        if powered_by:
            findings.append(self._finding(
                severity=Severity.LOW,
                title="Technology Stack Disclosed via X-Powered-By",
                description=f"The X-Powered-By header reveals: '{powered_by}'. This discloses the server-side technology, making targeted attacks easier.",
                remediation="Remove the X-Powered-By header. In Express.js: app.disable('x-powered-by'). In PHP: expose_php = Off in php.ini.",
                evidence=f"X-Powered-By: {powered_by}",
                confidence=Confidence.HIGH,
            ))

        # Check X-AspNet-Version
        aspnet = headers_lower.get("x-aspnet-version", "")
        if aspnet:
            findings.append(self._finding(
                severity=Severity.LOW,
                title="ASP.NET Version Disclosed",
                description=f"The X-AspNet-Version header reveals: '{aspnet}'.",
                remediation="Add <httpRuntime enableVersionHeader=\"false\" /> in web.config.",
                evidence=f"X-AspNet-Version: {aspnet}",
                confidence=Confidence.HIGH,
            ))

        return findings

    async def _check_exposed_files(self) -> list[FindingData]:
        findings = []

        async def check_file(path: str, desc: str):
            resp = await self._get(path)
            if resp is None or resp.status_code != 200:
                return
            # Verify it's actual content, not a custom 404
            if len(resp.text) < 10:
                return
            lower = resp.text.lower()
            if "not found" in lower or "404" in lower or "<html" in lower[:100]:
                # Skip HTML pages (likely custom 404s) unless it's phpinfo
                if path != "/phpinfo.php":
                    return

            findings.append(self._finding(
                severity=Severity.HIGH if path in ("/.env", "/.git/HEAD", "/wp-config.php", "/database.yml") else Severity.MEDIUM,
                title=f"Exposed Sensitive File: {path}",
                description=f"The file '{path}' ({desc}) is publicly accessible. This may expose sensitive configuration data, credentials, or internal details.",
                remediation=f"Block access to '{path}' in your web server configuration. Move sensitive files outside the web root.",
                url=self._url(path),
                evidence=resp.text[:300],
                confidence=Confidence.HIGH,
            ))

        await asyncio.gather(*[check_file(p, d) for p, d in self.EXPOSED_FILES])
        return findings

    async def _check_cors(self) -> list[FindingData]:
        findings = []
        # Test with evil origin
        resp = await self._get(headers={"Origin": "https://evil-attacker.com"})
        if resp is None:
            return []

        acao = resp.headers.get("access-control-allow-origin", "")

        if acao == "*":
            findings.append(self._finding(
                severity=Severity.MEDIUM,
                title="CORS Allows All Origins (Wildcard)",
                description="The Access-Control-Allow-Origin header is set to '*', allowing any website to make cross-origin requests. If the API handles sensitive data or uses cookies, this is a security risk.",
                remediation="Restrict CORS to specific trusted origins instead of using '*'. Example: Access-Control-Allow-Origin: https://yourdomain.com",
                evidence="Access-Control-Allow-Origin: *",
                confidence=Confidence.HIGH,
            ))
        elif "evil-attacker.com" in acao:
            acac = resp.headers.get("access-control-allow-credentials", "")
            findings.append(self._finding(
                severity=Severity.HIGH if acac.lower() == "true" else Severity.MEDIUM,
                title="CORS Reflects Arbitrary Origin",
                description=f"The server reflects the attacker-controlled Origin header back in Access-Control-Allow-Origin. {'Combined with Allow-Credentials: true, this allows attackers to steal authenticated data cross-origin.' if acac.lower() == 'true' else 'An attacker could make cross-origin requests from any domain.'}",
                remediation="Validate the Origin header against a whitelist of trusted domains. Never reflect the Origin header directly.",
                evidence=f"Sent Origin: https://evil-attacker.com\nReceived ACAO: {acao}\nACAC: {acac}",
                confidence=Confidence.HIGH,
            ))

        return findings

    async def _check_cookie_flags(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]

        for cookie in cookies:
            lower = cookie.lower()
            name = cookie.split("=")[0].strip()

            issues = []
            if "secure" not in lower:
                issues.append("Secure")
            if "httponly" not in lower:
                issues.append("HttpOnly")
            if "samesite" not in lower:
                issues.append("SameSite")

            if issues:
                findings.append(self._finding(
                    severity=Severity.MEDIUM if "Secure" in issues or "HttpOnly" in issues else Severity.LOW,
                    title=f"Cookie '{name}' Missing Security Flags: {', '.join(issues)}",
                    description=f"The cookie '{name}' is missing the following security attributes: {', '.join(issues)}. Without these flags, the cookie may be vulnerable to interception (missing Secure), XSS theft (missing HttpOnly), or CSRF attacks (missing SameSite).",
                    remediation=f"Set the cookie with all security flags: Set-Cookie: {name}=value; Secure; HttpOnly; SameSite=Lax",
                    evidence=cookie[:200],
                    confidence=Confidence.HIGH,
                ))

        return findings
