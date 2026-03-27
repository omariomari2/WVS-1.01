import asyncio
import math
import re
from collections import Counter

from bs4 import BeautifulSoup

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class AuthFailuresScanner(BaseScannerModule):
    category = "A07"
    name = "Identification and Authentication Failures"
    description = "Checks login forms, session cookies, password policies, and username enumeration."

    LOGIN_PATHS = ["/login", "/signin", "/auth/login", "/account/login", "/wp-login.php"]

    async def scan(self) -> list[FindingData]:
        results = await asyncio.gather(
            self._check_login_form(),
            self._check_session_cookies(),
            self._check_username_enumeration(),
        )
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_login_form(self) -> list[FindingData]:
        findings = []

        for path in self.LOGIN_PATHS:
            resp = await self._get(path)
            if resp is None or resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            forms = soup.find_all("form")
            for form in forms:
                password_fields = form.find_all("input", attrs={"type": "password"})
                if not password_fields:
                    continue

                # Check form action uses HTTPS
                action = form.get("action", "")
                if action.startswith("http://"):
                    findings.append(self._finding(
                        severity=Severity.CRITICAL,
                        title=f"Login Form Submits Over HTTP ({path})",
                        description=f"The login form at '{path}' submits credentials to an HTTP (non-HTTPS) URL: '{action}'. Credentials are sent in plaintext and can be intercepted.",
                        remediation="Ensure the form action URL uses HTTPS. Redirect all HTTP traffic to HTTPS.",
                        url=self._url(path),
                        evidence=f"Form action: {action}",
                        confidence=Confidence.HIGH,
                    ))

                # Check autocomplete on password fields
                for pwd_field in password_fields:
                    autocomplete = pwd_field.get("autocomplete", "")
                    if autocomplete != "off" and autocomplete != "new-password" and autocomplete != "current-password":
                        findings.append(self._finding(
                            severity=Severity.LOW,
                            title=f"Password Field Allows Autocomplete ({path})",
                            description=f"The password field at '{path}' does not have autocomplete disabled. Browsers may store the password, which could be accessed by others using the same device.",
                            remediation='Add autocomplete="new-password" or autocomplete="off" to the password input field.',
                            url=self._url(path),
                            evidence=f"Password field HTML: {str(pwd_field)[:200]}",
                            confidence=Confidence.MEDIUM,
                        ))

                return findings  # Only need to check first login form found

        return findings

    async def _check_session_cookies(self) -> list[FindingData]:
        resp = await self._get()
        if resp is None:
            return []

        findings = []
        cookies = [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]

        session_patterns = ["session", "sess", "sid", "token", "auth", "jwt"]

        for cookie in cookies:
            name = cookie.split("=")[0].strip().lower()
            is_session = any(p in name for p in session_patterns)
            if not is_session:
                continue

            # Check cookie value entropy
            value_part = cookie.split(";")[0]
            if "=" in value_part:
                cookie_value = value_part.split("=", 1)[1]
                entropy = self._calculate_entropy(cookie_value)
                if entropy < 3.0 and len(cookie_value) > 0:
                    findings.append(self._finding(
                        severity=Severity.HIGH,
                        title=f"Low-Entropy Session Cookie: {name}",
                        description=f"The session cookie '{name}' has low entropy ({entropy:.1f} bits/char), suggesting it may be predictable. Attackers could guess or brute-force session IDs.",
                        remediation="Use a cryptographically secure random number generator for session IDs. Session IDs should be at least 128 bits of entropy.",
                        evidence=f"Cookie value length: {len(cookie_value)}, Entropy: {entropy:.2f} bits/char",
                        confidence=Confidence.MEDIUM,
                    ))

        return findings

    async def _check_username_enumeration(self) -> list[FindingData]:
        findings = []

        for path in self.LOGIN_PATHS:
            resp = await self._get(path)
            if resp is None or resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            forms = soup.find_all("form")

            for form in forms:
                password_fields = form.find_all("input", attrs={"type": "password"})
                if not password_fields:
                    continue

                # Find username/email field
                text_inputs = form.find_all("input", attrs={"type": ["text", "email"]})
                if not text_inputs:
                    continue

                username_field = text_inputs[0].get("name", "username")
                password_field = password_fields[0].get("name", "password")
                action = form.get("action", path)
                method = form.get("method", "post").upper()

                # Try with a definitely-wrong username
                data1 = {username_field: "venomai_nonexistent_user_test_123", password_field: "wrongpassword"}
                # Try with a common username
                data2 = {username_field: "admin", password_field: "wrongpassword"}

                try:
                    if method == "POST":
                        resp1 = await self.client.post(self._url(action), data=data1)
                        resp2 = await self.client.post(self._url(action), data=data2)
                    else:
                        continue  # Skip GET login forms

                    if resp1 and resp2:
                        # Compare response bodies (ignoring CSRF tokens, etc.)
                        body1 = re.sub(r'value="[^"]*"', '', resp1.text)
                        body2 = re.sub(r'value="[^"]*"', '', resp2.text)

                        if body1 != body2 and resp1.status_code == resp2.status_code:
                            findings.append(self._finding(
                                severity=Severity.MEDIUM,
                                title=f"Possible Username Enumeration ({path})",
                                description=f"The login form at '{path}' returns different responses for valid vs invalid usernames. This allows attackers to enumerate valid accounts.",
                                remediation="Use identical error messages regardless of whether the username or password is wrong. Example: 'Invalid credentials' for all login failures.",
                                url=self._url(path),
                                evidence="Different response bodies for existing vs non-existing usernames.",
                                confidence=Confidence.LOW,
                            ))
                except Exception:
                    pass

                return findings

        return findings

    @staticmethod
    def _calculate_entropy(s: str) -> float:
        if not s:
            return 0.0
        counter = Counter(s)
        length = len(s)
        entropy = 0.0
        for count in counter.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy
