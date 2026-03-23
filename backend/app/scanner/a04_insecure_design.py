import asyncio
import re

from bs4 import BeautifulSoup

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class InsecureDesignScanner(BaseScannerModule):
    category = "A04"
    name = "Insecure Design"
    description = "Checks for rate limiting, missing CAPTCHA, information disclosure in errors, and predictable resource IDs."

    LOGIN_PATHS = ["/login", "/signin", "/auth/login", "/account/login", "/wp-login.php"]
    SIGNUP_PATHS = ["/register", "/signup", "/auth/register", "/account/register"]
    RESET_PATHS = ["/forgot-password", "/reset-password", "/password/reset", "/auth/forgot"]

    STACK_TRACE_PATTERNS = [
        r"Traceback \(most recent call last\)",
        r"at \w+\.java:\d+",
        r"at .+\.cs:line \d+",
        r"Fatal error:.+on line \d+",
        r"Stack trace:",
        r"Exception in thread",
        r"node_modules/",
        r"vendor/",
    ]

    async def scan(self) -> list[FindingData]:
        results = await asyncio.gather(
            self._check_rate_limiting(),
            self._check_missing_captcha(),
            self._check_error_disclosure(),
            self._check_predictable_ids(),
        )
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_rate_limiting(self) -> list[FindingData]:
        # Find a login or sensitive endpoint to test
        target_path = None
        for path in self.LOGIN_PATHS + self.RESET_PATHS:
            resp = await self._get(path)
            if resp and resp.status_code == 200:
                target_path = path
                break

        if not target_path:
            return []

        # Send rapid requests
        responses = await asyncio.gather(
            *[self._get(target_path) for _ in range(15)]
        )

        success_count = sum(1 for r in responses if r and r.status_code == 200)
        if success_count >= 14:
            return [self._finding(
                severity=Severity.MEDIUM,
                title=f"No Rate Limiting on {target_path}",
                description=f"Sent 15 rapid requests to '{target_path}' and all returned 200 OK. The endpoint does not appear to enforce rate limiting, making it vulnerable to brute-force attacks.",
                remediation="Implement rate limiting on authentication and sensitive endpoints. Use progressive delays, CAPTCHA challenges, or account lockout after failed attempts.",
                url=self._url(target_path),
                evidence=f"{success_count}/15 requests returned 200 OK",
                confidence=Confidence.MEDIUM,
            )]

        return []

    async def _check_missing_captcha(self) -> list[FindingData]:
        findings = []

        for paths, form_type in [
            (self.LOGIN_PATHS, "login"),
            (self.SIGNUP_PATHS, "registration"),
            (self.RESET_PATHS, "password reset"),
        ]:
            for path in paths:
                resp = await self._get(path)
                if resp is None or resp.status_code != 200:
                    continue
                html = resp.text.lower()
                has_form = "<form" in html
                has_captcha = any(s in html for s in [
                    "recaptcha", "hcaptcha", "captcha", "turnstile",
                    "g-recaptcha", "cf-turnstile",
                ])
                if has_form and not has_captcha:
                    findings.append(self._finding(
                        severity=Severity.LOW,
                        title=f"No CAPTCHA on {form_type} Form ({path})",
                        description=f"The {form_type} form at '{path}' does not appear to include any CAPTCHA challenge. This makes it easier for automated tools to perform credential stuffing or spam registration.",
                        remediation=f"Add a CAPTCHA solution (reCAPTCHA, hCaptcha, or Cloudflare Turnstile) to the {form_type} form.",
                        url=self._url(path),
                        confidence=Confidence.MEDIUM,
                    ))
                    break  # One per form type

        return findings

    async def _check_error_disclosure(self) -> list[FindingData]:
        findings = []

        # Trigger errors with various methods
        error_triggers = [
            ("/this-should-not-exist-venomai-404-test", "404"),
            ("/%00", "null byte"),
            ("/a" * 500, "long URL"),
        ]

        for path, trigger_type in error_triggers:
            resp = await self._get(path)
            if resp is None:
                continue
            body = resp.text
            for pattern in self.STACK_TRACE_PATTERNS:
                if re.search(pattern, body, re.IGNORECASE):
                    findings.append(self._finding(
                        severity=Severity.MEDIUM,
                        title=f"Stack Trace/Debug Info Disclosed in Error Response",
                        description=f"The server returned detailed error information (stack traces, file paths, or framework details) when triggered with a {trigger_type} request. This information helps attackers understand the server's technology stack and find further vulnerabilities.",
                        remediation="Configure custom error pages that show generic messages to users. Disable debug mode in production. Log detailed errors server-side only.",
                        url=self._url(path),
                        evidence=body[:500],
                        confidence=Confidence.HIGH,
                    ))
                    return findings

        return findings

    async def _check_predictable_ids(self) -> list[FindingData]:
        # Check if sequential numeric IDs are used in common API paths
        test_paths = [
            "/api/users/1", "/api/users/2",
            "/user/1", "/user/2",
            "/api/posts/1", "/api/posts/2",
            "/api/orders/1", "/api/orders/2",
        ]

        success_count = 0
        successful_paths = []

        for path in test_paths:
            resp = await self._get(path)
            if resp and resp.status_code == 200 and len(resp.text) > 50:
                lower = resp.text.lower()
                if "not found" not in lower and "404" not in lower:
                    success_count += 1
                    successful_paths.append(path)

        if success_count >= 2:
            return [self._finding(
                severity=Severity.MEDIUM,
                title="Predictable/Sequential Resource IDs",
                description=f"Multiple resources with sequential numeric IDs are accessible ({', '.join(successful_paths[:4])}). Predictable IDs make it easy for attackers to enumerate and access resources belonging to other users (IDOR).",
                remediation="Use UUIDs or other non-sequential identifiers for resources. Always verify that the authenticated user has permission to access the requested resource.",
                evidence=f"Accessible paths with sequential IDs: {', '.join(successful_paths)}",
                confidence=Confidence.LOW,
            )]

        return []
