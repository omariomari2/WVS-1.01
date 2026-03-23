import asyncio

from app.scanner.base import BaseScannerModule, FindingData
from app.scanner.severity import Confidence, Severity


class BrokenAccessControlScanner(BaseScannerModule):
    category = "A01"
    name = "Broken Access Control"
    description = "Checks for directory traversal, exposed admin panels, HTTP method tampering, and directory listings."

    TRAVERSAL_PAYLOADS = [
        "/../../../etc/passwd",
        "/..%2f..%2f..%2fetc/passwd",
        "/....//....//....//etc/passwd",
    ]
    TRAVERSAL_SIGNATURES = ["root:x:", "root:*:", "[boot loader]", "[operating systems]"]

    SENSITIVE_PATHS = [
        "/admin", "/admin/", "/administrator", "/dashboard",
        "/api/users", "/api/admin", "/wp-admin", "/cpanel",
        "/management", "/manager", "/console",
    ]

    DIRECTORY_LISTING_PATHS = [
        "/assets/", "/uploads/", "/static/", "/images/",
        "/backup/", "/backups/", "/tmp/", "/temp/",
    ]
    DIRECTORY_LISTING_SIGNATURES = ["Index of", "<pre>", "Parent Directory", "[To Parent Directory]"]

    async def scan(self) -> list[FindingData]:
        results = await asyncio.gather(
            self._check_directory_traversal(),
            self._check_sensitive_paths(),
            self._check_directory_listing(),
            self._check_method_tampering(),
        )
        findings = []
        for result in results:
            findings.extend(result)
        return findings

    async def _check_directory_traversal(self) -> list[FindingData]:
        findings = []
        for payload in self.TRAVERSAL_PAYLOADS:
            resp = await self._get(payload)
            if resp is None:
                continue
            body = resp.text.lower()
            for sig in self.TRAVERSAL_SIGNATURES:
                if sig.lower() in body:
                    findings.append(self._finding(
                        severity=Severity.CRITICAL,
                        title="Directory Traversal Vulnerability",
                        description=f"The server responded with sensitive file content when requesting the path '{payload}'. This indicates a path traversal vulnerability that allows reading arbitrary files on the server.",
                        remediation="Validate and sanitize all user-supplied file paths. Use a whitelist of allowed paths. Never pass user input directly to file system operations.",
                        url=self._url(payload),
                        evidence=resp.text[:500],
                        confidence=Confidence.HIGH,
                    ))
                    return findings  # One finding is enough
        return findings

    async def _check_sensitive_paths(self) -> list[FindingData]:
        findings = []

        async def check_path(path: str):
            resp = await self._get(path)
            if resp and resp.status_code == 200 and len(resp.text) > 100:
                # Check it's not a generic 404 page served with 200
                lower = resp.text.lower()
                if "not found" not in lower and "404" not in lower:
                    findings.append(self._finding(
                        severity=Severity.HIGH,
                        title=f"Potentially Exposed Admin/Sensitive Path: {path}",
                        description=f"The path '{path}' returned a 200 OK response with content. This may indicate an exposed administrative interface or sensitive endpoint that lacks proper access controls.",
                        remediation="Restrict access to administrative and sensitive paths using authentication and authorization. Return 403 or 404 for unauthorized users.",
                        url=self._url(path),
                        evidence=f"Status: {resp.status_code}, Content-Length: {len(resp.text)}",
                        confidence=Confidence.LOW,
                    ))

        await asyncio.gather(*[check_path(p) for p in self.SENSITIVE_PATHS])
        return findings

    async def _check_directory_listing(self) -> list[FindingData]:
        findings = []

        async def check_dir(path: str):
            resp = await self._get(path)
            if resp is None or resp.status_code != 200:
                return
            for sig in self.DIRECTORY_LISTING_SIGNATURES:
                if sig in resp.text:
                    findings.append(self._finding(
                        severity=Severity.MEDIUM,
                        title=f"Directory Listing Enabled: {path}",
                        description=f"Directory listing is enabled at '{path}'. This allows attackers to browse the directory structure and discover sensitive files.",
                        remediation="Disable directory listing in your web server configuration (e.g., 'Options -Indexes' in Apache, 'autoindex off' in Nginx).",
                        url=self._url(path),
                        evidence=resp.text[:300],
                        confidence=Confidence.HIGH,
                    ))
                    return

        await asyncio.gather(*[check_dir(p) for p in self.DIRECTORY_LISTING_PATHS])
        return findings

    async def _check_method_tampering(self) -> list[FindingData]:
        findings = []
        # First get the main page to find if it exists
        resp = await self._get()
        if resp is None:
            return findings

        for method in ["PUT", "DELETE", "PATCH"]:
            resp = await self._request(method)
            if resp and resp.status_code == 200:
                findings.append(self._finding(
                    severity=Severity.MEDIUM,
                    title=f"HTTP {method} Method Allowed on Root",
                    description=f"The server accepted an HTTP {method} request on the root URL and returned 200 OK. This may indicate overly permissive method handling.",
                    remediation=f"Restrict HTTP methods to only those required (typically GET and POST). Return 405 Method Not Allowed for unsupported methods.",
                    evidence=f"HTTP {method} returned status {resp.status_code}",
                    confidence=Confidence.LOW,
                ))
        return findings
