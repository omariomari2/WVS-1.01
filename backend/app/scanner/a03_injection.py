import asyncio
import re
from urllib.parse import parse_qs, urlencode, urlparse

from bs4 import BeautifulSoup

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class InjectionScanner(BaseScannerModule):
    category = "A03"
    name = "Injection"
    description = "Checks for reflected XSS, SQL injection indicators, command injection, and CRLF injection."

    XSS_PAYLOADS = [
        "<script>venom_xss_test</script>",
        '"><img src=x onerror=venom_xss>',
        "'-alert('venom')-'",
    ]

    SQLI_PAYLOADS = [
        "'",
        "1' OR '1'='1",
        "1; SELECT 1--",
        "1 UNION SELECT NULL--",
    ]

    SQL_ERROR_PATTERNS = [
        r"you have an error in your sql syntax",
        r"unclosed quotation mark",
        r"mysql_fetch",
        r"pg_query",
        r"sqlite3\.OperationalError",
        r"ORA-\d{5}",
        r"Microsoft OLE DB Provider",
        r"ODBC SQL Server Driver",
        r"javax\.persistence",
        r"SQL syntax.*MySQL",
        r"Warning.*\Wpg_",
        r"valid PostgreSQL result",
        r"Npgsql\.",
        r"SQLite\/JDBCDriver",
        r"System\.Data\.SQLite\.SQLiteException",
    ]

    CMDI_PAYLOADS = [
        "; echo venom_cmd_test",
        "| echo venom_cmd_test",
        "` echo venom_cmd_test`",
    ]

    async def scan(self) -> list[FindingData]:
        # First, fetch the page and extract forms and query params
        resp = await self._get()
        if resp is None:
            return []

        params = self._extract_params(resp.url)
        forms = self._extract_forms(resp.text)

        results = await asyncio.gather(
            self._check_reflected_xss(params),
            self._check_sql_injection(params),
            self._check_command_injection(params),
            self._check_crlf_injection(params),
            self._check_form_xss(forms),
        )

        findings = []
        for result in results:
            findings.extend(result)
        return findings

    def _extract_params(self, url) -> dict[str, str]:
        parsed = urlparse(str(url))
        qs = parse_qs(parsed.query)
        return {k: v[0] for k, v in qs.items()}

    def _extract_forms(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        forms = []
        for form in soup.find_all("form"):
            action = form.get("action", "")
            method = form.get("method", "get").upper()
            inputs = []
            for inp in form.find_all(["input", "textarea", "select"]):
                name = inp.get("name")
                if name:
                    inputs.append({
                        "name": name,
                        "type": inp.get("type", "text"),
                        "value": inp.get("value", "test"),
                    })
            if inputs:
                forms.append({"action": action, "method": method, "inputs": inputs})
        return forms

    async def _check_reflected_xss(self, params: dict) -> list[FindingData]:
        if not params:
            return []

        findings = []
        for payload in self.XSS_PAYLOADS:
            for param_name in params:
                test_params = {**params, param_name: payload}
                qs = urlencode(test_params)
                test_url = f"{self.target_url}?{qs}"
                resp = await self._get(f"?{qs}")
                if resp is None:
                    continue
                if payload in resp.text:
                    findings.append(self._finding(
                        severity=Severity.HIGH,
                        title=f"Reflected XSS via Parameter '{param_name}'",
                        description=f"The parameter '{param_name}' reflects user input back into the page without proper encoding. An attacker could inject malicious JavaScript that executes in victims' browsers.",
                        remediation="Encode all user input before rendering it in HTML. Use context-appropriate encoding (HTML entities for HTML context, JavaScript encoding for JS context). Implement Content-Security-Policy headers.",
                        url=test_url,
                        evidence=f"Payload '{payload}' was reflected unescaped in the response body.",
                        confidence=Confidence.HIGH,
                    ))
                    return findings  # One confirmed XSS is enough
        return findings

    async def _check_sql_injection(self, params: dict) -> list[FindingData]:
        if not params:
            return []

        findings = []
        for payload in self.SQLI_PAYLOADS:
            for param_name in params:
                test_params = {**params, param_name: payload}
                qs = urlencode(test_params)
                resp = await self._get(f"?{qs}")
                if resp is None:
                    continue
                body = resp.text.lower()
                for pattern in self.SQL_ERROR_PATTERNS:
                    if re.search(pattern, body, re.IGNORECASE):
                        findings.append(self._finding(
                            severity=Severity.CRITICAL,
                            title=f"SQL Injection Indicator via Parameter '{param_name}'",
                            description=f"The parameter '{param_name}' triggered a database error message when injected with SQL syntax. This strongly indicates a SQL injection vulnerability that could allow an attacker to read, modify, or delete database contents.",
                            remediation="Use parameterized queries (prepared statements) for all database operations. Never concatenate user input into SQL strings. Use an ORM where possible.",
                            url=self._url(f"?{qs}"),
                            evidence=f"Payload: {payload}\nSQL error pattern matched: {pattern}",
                            confidence=Confidence.HIGH,
                        ))
                        return findings
        return findings

    async def _check_command_injection(self, params: dict) -> list[FindingData]:
        if not params:
            return []

        findings = []
        for payload in self.CMDI_PAYLOADS:
            for param_name in params:
                test_params = {**params, param_name: payload}
                qs = urlencode(test_params)
                resp = await self._get(f"?{qs}")
                if resp is None:
                    continue
                if "venom_cmd_test" in resp.text:
                    findings.append(self._finding(
                        severity=Severity.CRITICAL,
                        title=f"Command Injection via Parameter '{param_name}'",
                        description=f"The parameter '{param_name}' appears to allow OS command injection. The server executed a test command and returned its output. An attacker could execute arbitrary commands on the server.",
                        remediation="Never pass user input to shell commands. Use language-native libraries instead of shell execution. If shell commands are necessary, use strict input validation and allowlisting.",
                        url=self._url(f"?{qs}"),
                        evidence=f"Payload: {payload}\nOutput 'venom_cmd_test' appeared in response.",
                        confidence=Confidence.HIGH,
                    ))
                    return findings
        return findings

    async def _check_crlf_injection(self, params: dict) -> list[FindingData]:
        if not params:
            return []

        findings = []
        crlf_payload = "%0d%0aX-Venom-Injected:true"
        for param_name in params:
            test_params = {**params, param_name: crlf_payload}
            qs = urlencode(test_params, safe="%")
            resp = await self._get(f"?{qs}")
            if resp is None:
                continue
            if "x-venom-injected" in {k.lower() for k in resp.headers.keys()}:
                findings.append(self._finding(
                    severity=Severity.HIGH,
                    title=f"CRLF Injection via Parameter '{param_name}'",
                    description=f"The parameter '{param_name}' is vulnerable to CRLF injection. An attacker can inject arbitrary HTTP headers, potentially enabling cache poisoning, XSS, or session fixation.",
                    remediation="Strip or encode CR (\\r) and LF (\\n) characters from all user input used in HTTP headers. Use framework-provided header-setting functions.",
                    url=self._url(f"?{qs}"),
                    evidence="Injected header 'X-Venom-Injected' appeared in the response.",
                    confidence=Confidence.HIGH,
                ))
                return findings
        return findings

    async def _check_form_xss(self, forms: list[dict]) -> list[FindingData]:
        findings = []
        payload = "<script>venom_form_xss</script>"

        for form in forms[:5]:  # Limit to first 5 forms
            data = {}
            for inp in form["inputs"]:
                if inp["type"] in ("text", "search", "email", "url", "textarea"):
                    data[inp["name"]] = payload
                else:
                    data[inp["name"]] = inp["value"]

            action = form["action"] or ""
            if form["method"] == "POST":
                try:
                    resp = await self.client.post(self._url(action), data=data)
                except Exception:
                    continue
            else:
                qs = urlencode(data)
                resp = await self._get(f"{action}?{qs}" if action else f"?{qs}")

            if resp and payload in resp.text:
                findings.append(self._finding(
                    severity=Severity.HIGH,
                    title=f"Reflected XSS via Form (action='{action or '/'}')",
                    description="A form on the page reflects submitted input without proper encoding, allowing injection of arbitrary HTML/JavaScript.",
                    remediation="Encode all user input before rendering. Use Content-Security-Policy headers. Apply input validation on form fields.",
                    url=self._url(action) if action else self.target_url,
                    evidence=f"Form method: {form['method']}, Payload reflected in response body.",
                    confidence=Confidence.HIGH,
                ))
                break  # One form XSS finding is enough

        return findings
