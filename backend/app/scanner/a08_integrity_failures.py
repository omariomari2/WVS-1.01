import asyncio
import base64
import re

from bs4 import BeautifulSoup

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class IntegrityFailuresScanner(BaseScannerModule):
    category = "A08"
    name = "Software and Data Integrity Failures"
    description = "Checks for missing Subresource Integrity (SRI), insecure deserialization indicators, and exposed CI/CD files."

    CI_CD_PATHS = [
        "/.github/workflows/",
        "/Jenkinsfile",
        "/.gitlab-ci.yml",
        "/.circleci/config.yml",
        "/Dockerfile",
        "/docker-compose.yml",
        "/.travis.yml",
        "/bitbucket-pipelines.yml",
    ]

    # Java serialized object magic bytes (base64 encoded start)
    SERIALIZATION_PATTERNS = [
        (r"rO0AB", "Java serialized object"),
        (r"O:\d+:", "PHP serialized object"),
        (r"gAJ", "Python pickle (protocol 2)"),
        (r"\x80\x03", "Python pickle (protocol 3)"),
    ]

    async def scan(self) -> list[FindingData]:
        results = await asyncio.gather(
            self._check_sri(),
            self._check_deserialization_cookies(),
            self._check_cicd_exposure(),
        )
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_sri(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        findings = []
        missing_sri = []

        # Check <script> tags from external CDNs
        for tag in soup.find_all("script", src=True):
            src = tag.get("src", "")
            if self._is_external_cdn(src) and not tag.get("integrity"):
                missing_sri.append(f"<script src=\"{src}\">")

        # Check <link> tags from external CDNs
        for tag in soup.find_all("link", href=True):
            href = tag.get("href", "")
            rel = tag.get("rel", [])
            if "stylesheet" in rel and self._is_external_cdn(href) and not tag.get("integrity"):
                missing_sri.append(f"<link href=\"{href}\">")

        if missing_sri:
            findings.append(self._finding(
                severity=Severity.MEDIUM,
                title=f"Missing Subresource Integrity (SRI) on {len(missing_sri)} CDN Resource(s)",
                description=f"Found {len(missing_sri)} external resource(s) loaded from CDNs without Subresource Integrity (SRI) hashes. If the CDN is compromised, malicious code could be injected into your page.",
                remediation="Add integrity attributes to all external script and link tags. Example: <script src=\"...\" integrity=\"sha384-...\" crossorigin=\"anonymous\">. Use https://www.srihash.org/ to generate hashes.",
                evidence="\n".join(missing_sri[:5]),
                confidence=Confidence.HIGH,
            ))

        return findings

    async def _check_deserialization_cookies(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        cookies = [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]

        for cookie in cookies:
            name = cookie.split("=")[0].strip()
            value_part = cookie.split(";")[0]
            if "=" in value_part:
                cookie_value = value_part.split("=", 1)[1]

                # Try base64 decode
                try:
                    decoded = base64.b64decode(cookie_value + "==").decode("latin-1")
                except Exception:
                    decoded = cookie_value

                for pattern, obj_type in self.SERIALIZATION_PATTERNS:
                    if re.search(pattern, cookie_value) or re.search(pattern, decoded):
                        findings.append(self._finding(
                            severity=Severity.HIGH,
                            title=f"Possible Serialized Object in Cookie: {name}",
                            description=f"The cookie '{name}' appears to contain a {obj_type}. If the application deserializes this cookie without validation, it may be vulnerable to insecure deserialization attacks that can lead to remote code execution.",
                            remediation="Never deserialize untrusted data. Use signed/encrypted tokens (like JWTs with signature verification) instead of serialized objects in cookies.",
                            evidence=f"Cookie value (truncated): {cookie_value[:100]}",
                            confidence=Confidence.LOW,
                        ))
                        break

        return findings

    async def _check_cicd_exposure(self) -> list[FindingData]:
        findings = []

        async def check_path(path: str):
            resp = await self._get(path)
            if resp is None or resp.status_code != 200:
                return
            if len(resp.text) < 10:
                return
            lower = resp.text.lower()
            if "not found" in lower or "404" in lower:
                return
            findings.append(self._finding(
                severity=Severity.HIGH,
                title=f"Exposed CI/CD Configuration: {path}",
                description=f"The CI/CD configuration file at '{path}' is publicly accessible. This may expose build secrets, deployment credentials, internal infrastructure details, and build pipeline logic.",
                remediation=f"Block access to '{path}' in your web server configuration. Ensure CI/CD files are not deployed to production servers.",
                url=self._url(path),
                evidence=resp.text[:300],
                confidence=Confidence.HIGH,
            ))

        await asyncio.gather(*[check_path(p) for p in self.CI_CD_PATHS])
        return findings

    @staticmethod
    def _is_external_cdn(url: str) -> bool:
        cdn_indicators = [
            "cdn.", "cdnjs.", "jsdelivr", "unpkg", "cloudflare",
            "bootstrapcdn", "googleapis.com", "gstatic.com",
            "ajax.aspnetcdn", "stackpath",
        ]
        url_lower = url.lower()
        return any(cdn in url_lower for cdn in cdn_indicators) or (
            url_lower.startswith("http") and "//" in url_lower
        )
