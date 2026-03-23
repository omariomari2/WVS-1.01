import asyncio
import re

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class LoggingMonitoringScanner(BaseScannerModule):
    category = "A09"
    name = "Security Logging and Monitoring Failures"
    description = "Checks error handling behavior, timing information leakage, security.txt, and verbose error pages."

    TIMING_HEADERS = [
        "x-runtime", "x-request-time", "x-response-time",
        "x-elapsed", "x-timer", "x-debug-time",
    ]

    async def scan(self) -> list[FindingData]:
        results = await asyncio.gather(
            self._check_error_handling(),
            self._check_timing_headers(),
            self._check_security_txt(),
            self._check_verbose_errors(),
        )
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_error_handling(self) -> list[FindingData]:
        findings = []

        # Send various malformed requests
        test_cases = [
            ("GET", "/%00%ff%fe", "null/invalid bytes"),
            ("GET", "/" + "A" * 5000, "oversized URL"),
        ]

        for method, path, desc in test_cases:
            resp = await self._request(method, path)
            if resp is None:
                continue

            body = resp.text
            debug_indicators = [
                r"Traceback \(most recent call last\)",
                r"at .+\.\w+\(.+:\d+\)",  # Java/C# stack trace
                r"File \"[^\"]+\", line \d+",  # Python
                r"in /.+\.php on line \d+",  # PHP
                r"Exception|Error at|STACK TRACE",
                r"<pre class=\"trace\">",  # Framework debug
            ]

            for pattern in debug_indicators:
                if re.search(pattern, body, re.IGNORECASE):
                    findings.append(self._finding(
                        severity=Severity.MEDIUM,
                        title=f"Verbose Error Response ({desc})",
                        description=f"A request with {desc} produced a response containing debug/stack trace information. Detailed error messages help attackers understand the application's internals.",
                        remediation="Implement custom error pages that show generic messages. Ensure debug mode is disabled in production.",
                        url=self._url(path[:100]),
                        evidence=body[:400],
                        confidence=Confidence.HIGH,
                    ))
                    return findings  # One is enough

        return findings

    async def _check_timing_headers(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}

        found_timing = []
        for header in self.TIMING_HEADERS:
            if header in headers_lower:
                found_timing.append(f"{header}: {headers_lower[header]}")

        if found_timing:
            findings.append(self._finding(
                severity=Severity.LOW,
                title="Server Timing Information Leaked in Headers",
                description=f"The server exposes timing information via response headers: {', '.join(found_timing)}. This data can help attackers perform timing-based attacks (e.g., determining if a user exists based on response time differences).",
                remediation="Remove timing-related headers in production. If needed for monitoring, expose them only to internal/authenticated requests.",
                evidence="\n".join(found_timing),
                confidence=Confidence.HIGH,
            ))

        return findings

    async def _check_security_txt(self) -> list[FindingData]:
        findings = []

        resp = await self._get("/.well-known/security.txt")
        if resp is None or resp.status_code != 200:
            # Also check root
            resp = await self._get("/security.txt")

        if resp is None or resp.status_code != 200:
            findings.append(self._finding(
                severity=Severity.INFORMATIONAL,
                title="Missing security.txt",
                description="No security.txt file was found at /.well-known/security.txt or /security.txt. This file helps security researchers responsibly disclose vulnerabilities they find in your application.",
                remediation="Create a security.txt file at /.well-known/security.txt with at least a Contact field. See https://securitytxt.org/ for the specification.",
                confidence=Confidence.HIGH,
            ))
        else:
            # Validate basic format
            text = resp.text
            has_contact = "Contact:" in text or "contact:" in text.lower()
            has_expires = "Expires:" in text or "expires:" in text.lower()

            if not has_contact:
                findings.append(self._finding(
                    severity=Severity.LOW,
                    title="security.txt Missing Required 'Contact' Field",
                    description="The security.txt file exists but is missing the required 'Contact' field. Without it, researchers cannot report vulnerabilities.",
                    remediation="Add a Contact field to security.txt. Example: Contact: mailto:security@yourdomain.com",
                    evidence=text[:300],
                    confidence=Confidence.HIGH,
                ))

            if not has_expires:
                findings.append(self._finding(
                    severity=Severity.INFORMATIONAL,
                    title="security.txt Missing 'Expires' Field",
                    description="The security.txt file is missing the recommended 'Expires' field to indicate when the file should be considered stale.",
                    remediation="Add an Expires field. Example: Expires: 2025-12-31T23:59:59z",
                    evidence=text[:300],
                    confidence=Confidence.HIGH,
                ))

        return findings

    async def _check_verbose_errors(self) -> list[FindingData]:
        findings = []

        # Send invalid HTTP method
        resp = await self._request("FOOBAR")
        if resp is None:
            return []

        body = resp.text
        verbose_indicators = [
            r"<title>.*error.*</title>",
            r"powered by",
            r"version \d+\.\d+",
            r"/usr/",
            r"C:\\",
            r"stack trace",
            r"debug",
        ]

        for pattern in verbose_indicators:
            if re.search(pattern, body, re.IGNORECASE):
                findings.append(self._finding(
                    severity=Severity.LOW,
                    title="Verbose Error Page on Invalid HTTP Method",
                    description="Sending an invalid HTTP method (FOOBAR) produced a response that may contain server internals, version information, or file paths.",
                    remediation="Configure generic error pages for all HTTP error codes. Ensure error pages do not leak server details.",
                    evidence=body[:400],
                    confidence=Confidence.LOW,
                ))
                return findings

        return findings
