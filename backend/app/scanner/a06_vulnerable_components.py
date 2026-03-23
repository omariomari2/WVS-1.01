import re

from bs4 import BeautifulSoup

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class VulnerableComponentsScanner(BaseScannerModule):
    category = "A06"
    name = "Vulnerable and Outdated Components"
    description = "Detects JavaScript libraries, server technologies, CMS platforms, and checks for known-vulnerable versions."

    # Known vulnerable version ranges (library -> list of (max_vulnerable_version, CVE/description))
    KNOWN_VULNERABILITIES = {
        "jquery": [
            ("1.12.4", "jQuery < 1.12.4 has XSS vulnerabilities (CVE-2015-9251)"),
            ("3.4.1", "jQuery < 3.5.0 has XSS via jQuery.htmlPrefilter (CVE-2020-11022)"),
        ],
        "angular": [
            ("1.5.11", "AngularJS < 1.6.0 has multiple XSS vulnerabilities"),
        ],
        "bootstrap": [
            ("3.4.0", "Bootstrap < 3.4.1 has XSS in tooltip/popover (CVE-2019-8331)"),
        ],
        "lodash": [
            ("4.17.20", "Lodash < 4.17.21 has prototype pollution (CVE-2021-23337)"),
        ],
        "moment": [
            ("2.29.3", "Moment.js < 2.29.4 has ReDoS vulnerability (CVE-2022-31129)"),
        ],
    }

    JS_LIB_PATTERNS = [
        (r"jquery[.-](\d+\.\d+\.\d+)", "jquery"),
        (r"jquery\.min\.js\?v=(\d+\.\d+\.\d+)", "jquery"),
        (r"angular[.-](\d+\.\d+\.\d+)", "angular"),
        (r"bootstrap[.-](\d+\.\d+\.\d+)", "bootstrap"),
        (r"vue[.-](\d+\.\d+\.\d+)", "vue"),
        (r"react[.-](\d+\.\d+\.\d+)", "react"),
        (r"lodash[.-](\d+\.\d+\.\d+)", "lodash"),
        (r"moment[.-](\d+\.\d+\.\d+)", "moment"),
    ]

    CMS_CHECKS = [
        ("/wp-login.php", "WordPress"),
        ("/wp-admin/", "WordPress"),
        ("/administrator/", "Joomla"),
        ("/user/login", "Drupal"),
        ("/CHANGELOG.txt", "Drupal"),
    ]

    async def scan(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        findings.extend(self._detect_js_libraries(resp.text))
        findings.extend(self._detect_server_tech(resp.headers))
        findings.extend(await self._detect_cms())

        # Also check meta generator tag
        soup = BeautifulSoup(resp.text, "lxml")
        gen = soup.find("meta", attrs={"name": "generator"})
        if gen and gen.get("content"):
            content = gen["content"]
            findings.append(self._finding(
                severity=Severity.LOW,
                title=f"CMS/Framework Disclosed via Meta Generator: {content}",
                description=f"The HTML meta generator tag reveals: '{content}'. This helps attackers identify the exact technology and version in use.",
                remediation="Remove the meta generator tag from your HTML templates.",
                evidence=f'<meta name="generator" content="{content}">',
                confidence=Confidence.HIGH,
            ))

        return findings

    def _detect_js_libraries(self, html: str) -> list[FindingData]:
        findings = []
        detected = set()

        for pattern, lib_name in self.JS_LIB_PATTERNS:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for version in matches:
                key = f"{lib_name}-{version}"
                if key in detected:
                    continue
                detected.add(key)

                # Check for known vulnerabilities
                vulns = self.KNOWN_VULNERABILITIES.get(lib_name, [])
                is_vulnerable = False
                for max_vuln_ver, vuln_desc in vulns:
                    if self._version_lte(version, max_vuln_ver):
                        findings.append(self._finding(
                            severity=Severity.HIGH,
                            title=f"Vulnerable {lib_name} {version} Detected",
                            description=f"The page uses {lib_name} version {version}, which has known security vulnerabilities: {vuln_desc}",
                            remediation=f"Update {lib_name} to the latest stable version.",
                            evidence=f"Detected version: {version}",
                            confidence=Confidence.MEDIUM,
                        ))
                        is_vulnerable = True
                        break

                if not is_vulnerable:
                    findings.append(self._finding(
                        severity=Severity.INFORMATIONAL,
                        title=f"Detected {lib_name} {version}",
                        description=f"The page uses {lib_name} version {version}. No known vulnerabilities were found in the local database, but always verify against the latest CVE databases.",
                        remediation=f"Keep {lib_name} updated to the latest stable version. Monitor security advisories.",
                        evidence=f"Detected version: {version}",
                        confidence=Confidence.MEDIUM,
                    ))

        return findings

    def _detect_server_tech(self, headers) -> list[FindingData]:
        findings = []
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # X-Powered-By detection (detailed analysis)
        powered_by = headers_lower.get("x-powered-by", "")
        if powered_by:
            version_match = re.search(r"(\d+\.\d+[\.\d]*)", powered_by)
            if version_match:
                findings.append(self._finding(
                    severity=Severity.MEDIUM,
                    title=f"Server Technology with Version Detected: {powered_by}",
                    description=f"The X-Powered-By header reveals '{powered_by}' with version {version_match.group(1)}. Check if this version has known vulnerabilities.",
                    remediation="Remove the X-Powered-By header and keep the server technology updated.",
                    evidence=f"X-Powered-By: {powered_by}",
                    confidence=Confidence.HIGH,
                ))

        return findings

    async def _detect_cms(self) -> list[FindingData]:
        findings = []
        detected_cms = set()

        for path, cms_name in self.CMS_CHECKS:
            if cms_name in detected_cms:
                continue
            resp = await self._get(path)
            if resp and resp.status_code == 200:
                detected_cms.add(cms_name)
                findings.append(self._finding(
                    severity=Severity.INFORMATIONAL,
                    title=f"CMS Detected: {cms_name}",
                    description=f"{cms_name} was detected via the accessible path '{path}'. Ensure the CMS and all plugins are up to date.",
                    remediation=f"Keep {cms_name} and all its plugins/themes updated to the latest versions. Remove unused plugins.",
                    url=self._url(path),
                    evidence=f"Path '{path}' returned HTTP 200",
                    confidence=Confidence.MEDIUM,
                ))

        return findings

    @staticmethod
    def _version_lte(v1: str, v2: str) -> bool:
        """Check if version v1 <= v2."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            # Pad shorter version
            while len(parts1) < len(parts2):
                parts1.append(0)
            while len(parts2) < len(parts1):
                parts2.append(0)
            return parts1 <= parts2
        except ValueError:
            return False
