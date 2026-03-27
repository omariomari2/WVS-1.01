import asyncio
import re
from urllib.parse import parse_qs, urlencode, urlparse

from bs4 import BeautifulSoup

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class SSRFScanner(BaseScannerModule):
    category = "A10"
    name = "Server-Side Request Forgery (SSRF)"
    description = "Checks for URL parameters that may be vulnerable to SSRF, and tests for open redirects."

    URL_PARAM_NAMES = [
        "url", "uri", "redirect", "next", "callback", "return",
        "path", "src", "dest", "target", "link", "goto",
        "redirect_uri", "redirect_url", "return_url", "continue",
        "img", "image", "fetch", "proxy", "load",
    ]

    REDIRECT_TARGETS = [
        "https://evil-attacker.com",
        "//evil-attacker.com",
        "/\\evil-attacker.com",
    ]

    async def scan(self) -> list[FindingData]:
        # First fetch the page and look for URL-like parameters
        resp = await self._get()
        if resp is None:
            return []

        results = await asyncio.gather(
            self._check_url_params_in_query(resp),
            self._check_url_params_in_forms(resp.text),
            self._check_open_redirects(resp),
        )

        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_url_params_in_query(self, resp) -> list[FindingData]:
        findings = []
        parsed = urlparse(str(resp.url))
        params = parse_qs(parsed.query)

        # Check existing URL params
        for param_name, values in params.items():
            if param_name.lower() in self.URL_PARAM_NAMES:
                findings.extend(await self._test_ssrf_param(param_name, params))

        return findings

    async def _check_url_params_in_forms(self, html: str) -> list[FindingData]:
        findings = []
        soup = BeautifulSoup(html, "lxml")

        # Look for hidden inputs or inputs with URL-like names
        for inp in soup.find_all("input"):
            name = (inp.get("name") or "").lower()
            if name in self.URL_PARAM_NAMES:
                value = inp.get("value", "")
                if value and ("http" in value.lower() or "/" in value):
                    findings.append(self._finding(
                        severity=Severity.LOW,
                        title=f"URL-Accepting Form Parameter Found: {name}",
                        description=f"A form input named '{name}' with a URL-like value was found. If the server fetches this URL, it could be vulnerable to SSRF.",
                        remediation="Validate and whitelist URLs that the server is allowed to fetch. Block requests to internal IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254).",
                        evidence=f"Input: <input name=\"{name}\" value=\"{value[:100]}\">",
                        confidence=Confidence.LOW,
                    ))

        # Look for links with URL parameters
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            for param_name in params:
                if param_name.lower() in self.URL_PARAM_NAMES:
                    findings.append(self._finding(
                        severity=Severity.LOW,
                        title=f"URL Parameter in Link: {param_name}",
                        description=f"A link contains a URL parameter '{param_name}' which may be used for redirects or server-side fetching. If the server processes this URL, it could be vulnerable to SSRF or open redirect.",
                        remediation="Validate redirect URLs against a whitelist. Never allow redirects to arbitrary external domains.",
                        url=self._url(href) if not href.startswith("http") else href,
                        evidence=f"Link: {href[:200]}",
                        confidence=Confidence.LOW,
                    ))

        return findings[:5]  # Limit findings

    async def _check_open_redirects(self, initial_resp) -> list[FindingData]:
        findings = []

        # Find redirect-like parameters
        parsed = urlparse(str(initial_resp.url))
        params = parse_qs(parsed.query)

        # Also try common redirect parameter names even if not in current URL
        redirect_params = [p for p in params if p.lower() in self.URL_PARAM_NAMES]
        if not redirect_params:
            # Try adding common redirect params
            redirect_params = ["redirect", "next", "url", "return_url"]

        for param_name in redirect_params[:3]:
            for target in self.REDIRECT_TARGETS:
                test_params = {param_name: target}
                qs = urlencode(test_params)
                try:
                    # Don't follow redirects for this test
                    resp = await self.client.get(
                        self._url(f"?{qs}"),
                        follow_redirects=False,
                    )
                except Exception:
                    continue

                if resp is None:
                    continue

                # Check for redirect to our evil domain
                location = resp.headers.get("location", "")
                if resp.status_code in (301, 302, 303, 307, 308):
                    if "evil-attacker.com" in location:
                        findings.append(self._finding(
                            severity=Severity.HIGH,
                            title=f"Open Redirect via Parameter '{param_name}'",
                            description=f"The parameter '{param_name}' causes a redirect to an attacker-controlled domain. Open redirects can be used in phishing attacks to make malicious URLs appear legitimate.",
                            remediation="Validate redirect URLs against a whitelist of allowed domains. Only allow relative paths or pre-approved absolute URLs.",
                            url=self._url(f"?{qs}"),
                            evidence=f"Sent: {param_name}={target}\nRedirected to: {location}",
                            confidence=Confidence.HIGH,
                        ))
                        return findings  # One confirmed open redirect is enough

        return findings

    async def _test_ssrf_param(self, param_name: str, original_params: dict) -> list[FindingData]:
        findings = []

        # Test with internal IPs to see if behavior differs
        external_url = "https://httpbin.org/get"
        internal_urls = [
            "http://127.0.0.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
        ]

        # First, try external URL as baseline
        test_params = {k: v[0] if isinstance(v, list) else v for k, v in original_params.items()}
        test_params[param_name] = external_url
        qs = urlencode(test_params)
        baseline = await self._get(f"?{qs}")

        if baseline is None:
            return []

        for internal_url in internal_urls:
            test_params[param_name] = internal_url
            qs = urlencode(test_params)
            resp = await self._get(f"?{qs}")

            if resp is None:
                continue

            # If the response differs significantly from baseline, the server might be fetching the URL
            if abs(len(resp.text) - len(baseline.text)) > 100 and resp.status_code != baseline.status_code:
                findings.append(self._finding(
                    severity=Severity.HIGH,
                    title=f"Potential SSRF via Parameter '{param_name}'",
                    description=f"The parameter '{param_name}' shows different server behavior when provided internal vs external URLs. The server may be fetching the supplied URL, making it vulnerable to SSRF. An attacker could access internal services, cloud metadata endpoints, or other resources behind the firewall.",
                    remediation="Never fetch arbitrary user-supplied URLs on the server. If URL fetching is needed, implement a strict allowlist. Block all internal IP ranges and cloud metadata endpoints.",
                    url=self._url(f"?{qs}"),
                    evidence=f"External URL response: status={baseline.status_code}, length={len(baseline.text)}\nInternal URL ({internal_url}) response: status={resp.status_code}, length={len(resp.text)}",
                    confidence=Confidence.LOW,
                ))
                return findings

        return findings
