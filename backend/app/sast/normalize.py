from __future__ import annotations

from pathlib import Path
from typing import Any

from app.sast.base import ScanFinding, normalize_repo_path
from app.scanner.severity import Confidence, Severity


RULE_METADATA: dict[str, dict[str, Any]] = {
    "venomai.hardcoded-secrets.python.assignment": {
        "category": "hardcoded-secrets",
        "owasp": "A02",
        "cwe": "CWE-798",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "Hardcoded secret assignment",
        "remediation": "Move secrets to environment variables or a secrets manager.",
        "blocking_eligible": True,
    },
    "venomai.hardcoded-secrets.javascript.assignment": {
        "category": "hardcoded-secrets",
        "owasp": "A02",
        "cwe": "CWE-798",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "Hardcoded secret assignment",
        "remediation": "Move secrets to environment variables or a secrets manager.",
        "blocking_eligible": True,
    },
    "venomai.unsafe-input.python.dangerous-sink": {
        "category": "unsafe-input",
        "owasp": "A03",
        "cwe": "CWE-20",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "User input reaches a dangerous sink",
        "remediation": "Validate and sanitize the input before using it in dangerous sinks.",
        "blocking_eligible": False,
    },
    "venomai.unsafe-input.javascript.dangerous-sink": {
        "category": "unsafe-input",
        "owasp": "A03",
        "cwe": "CWE-20",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "User input reaches a dangerous sink",
        "remediation": "Validate and sanitize the input before using it in dangerous sinks.",
        "blocking_eligible": False,
    },
    "venomai.sql-injection.python.execute-string": {
        "category": "sql-injection",
        "owasp": "A03",
        "cwe": "CWE-89",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "SQL query built with string interpolation",
        "remediation": "Use parameterized queries or ORM query builders instead of string interpolation.",
        "blocking_eligible": True,
    },
    "venomai.sql-injection.javascript.query-string": {
        "category": "sql-injection",
        "owasp": "A03",
        "cwe": "CWE-89",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "SQL query built with string interpolation",
        "remediation": "Use parameterized queries or ORM query builders instead of string interpolation.",
        "blocking_eligible": True,
    },
    "venomai.weak-auth.python.weak-hash": {
        "category": "weak-authentication",
        "owasp": "A07",
        "cwe": "CWE-327",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "Weak password hashing",
        "remediation": "Use bcrypt, Argon2, or another adaptive password hashing algorithm.",
        "blocking_eligible": True,
    },
    "venomai.weak-auth.python.plaintext-password": {
        "category": "weak-authentication",
        "owasp": "A07",
        "cwe": "CWE-256",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "Plaintext password handling",
        "remediation": "Never store or compare plaintext passwords; hash them using bcrypt or Argon2.",
        "blocking_eligible": True,
    },
    "venomai.missing-authorization.fastapi.route": {
        "category": "missing-authorization",
        "owasp": "A01",
        "cwe": "CWE-862",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.LOW,
        "title": "Route may be missing authorization",
        "remediation": "Require an auth or permission dependency on state-changing endpoints.",
        "blocking_eligible": False,
    },
    "venomai.insecure-defaults.python.debug": {
        "category": "insecure-defaults",
        "owasp": "A05",
        "cwe": "CWE-16",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "Debug mode enabled",
        "remediation": "Disable debug mode in production-safe defaults.",
        "blocking_eligible": True,
    },
    "venomai.insecure-defaults.cors.wildcard": {
        "category": "insecure-defaults",
        "owasp": "A05",
        "cwe": "CWE-942",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "Wildcard CORS configuration",
        "remediation": "Restrict allowed origins to a defined allowlist.",
        "blocking_eligible": True,
    },
    "venomai.insecure-defaults.python.verify-disabled": {
        "category": "insecure-defaults",
        "owasp": "A05",
        "cwe": "CWE-295",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "TLS verification disabled",
        "remediation": "Keep TLS certificate verification enabled for outbound requests.",
        "blocking_eligible": True,
    },
    "venomai.xss.react.dangerous-html": {
        "category": "xss",
        "owasp": "A03",
        "cwe": "CWE-79",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "Unsanitized HTML rendering",
        "remediation": "Avoid raw HTML rendering or sanitize the content before rendering.",
        "blocking_eligible": True,
    },
    "venomai.xss.react.unsafe-markdown-html": {
        "category": "xss",
        "owasp": "A03",
        "cwe": "CWE-79",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "Markdown configured to allow raw HTML",
        "remediation": "Disable raw HTML rendering in markdown or sanitize content before rendering.",
        "blocking_eligible": True,
    },
    "venomai.unsafe-file.python.user-controlled-path": {
        "category": "unsafe-file-handling",
        "owasp": "A01",
        "cwe": "CWE-73",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "User-controlled file path",
        "remediation": "Validate filenames and store uploads under generated server-side paths.",
        "blocking_eligible": True,
    },
    "venomai.info-leak.python.raw-error": {
        "category": "information-leakage",
        "owasp": "A09",
        "cwe": "CWE-209",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.HIGH,
        "title": "Raw exception details exposed",
        "remediation": "Return generic error messages and log detailed context server-side.",
        "blocking_eligible": False,
    },
    "venomai.ssrf.python.user-url-fetch": {
        "category": "ssrf",
        "owasp": "A10",
        "cwe": "CWE-918",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "User-controlled URL fetch",
        "remediation": "Allowlist destinations and validate schemes and hosts before making outbound requests.",
        "blocking_eligible": True,
    },
    "venomai.path-traversal.python.user-path-open": {
        "category": "path-traversal",
        "owasp": "A01",
        "cwe": "CWE-22",
        "severity": Severity.HIGH,
        "confidence": Confidence.MEDIUM,
        "title": "User-controlled file path access",
        "remediation": "Normalize and validate paths against an allowlisted base directory.",
        "blocking_eligible": True,
    },
    "venomai.command-injection.python.shell-true": {
        "category": "command-injection",
        "owasp": "A03",
        "cwe": "CWE-78",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "Shell command built from dynamic input",
        "remediation": "Avoid shell invocation; use native APIs or pass fixed argument arrays without shell expansion.",
        "blocking_eligible": True,
    },
    "venomai.command-injection.javascript.exec-input": {
        "category": "command-injection",
        "owasp": "A03",
        "cwe": "CWE-78",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "Shell command built from dynamic input",
        "remediation": "Avoid shell invocation; use native APIs or pass fixed argument arrays without shell expansion.",
        "blocking_eligible": True,
    },
    "venomai.insecure-deserialization.python.pickle-loads": {
        "category": "insecure-deserialization",
        "owasp": "A08",
        "cwe": "CWE-502",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "Unsafe deserialization",
        "remediation": "Do not deserialize untrusted input with pickle or unsafe YAML loaders.",
        "blocking_eligible": True,
    },
    "venomai.insecure-deserialization.python.yaml-load": {
        "category": "insecure-deserialization",
        "owasp": "A08",
        "cwe": "CWE-502",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "Unsafe YAML loading",
        "remediation": "Use yaml.safe_load for untrusted content.",
        "blocking_eligible": True,
    },
    "venomai.open-redirect.fastapi.redirect-response": {
        "category": "open-redirect",
        "owasp": "A01",
        "cwe": "CWE-601",
        "severity": Severity.MEDIUM,
        "confidence": Confidence.MEDIUM,
        "title": "Potential open redirect",
        "remediation": "Allowlist redirect targets or validate that redirects stay on trusted hosts.",
        "blocking_eligible": False,
    },
}


GITLEAKS_RULE_METADATA = {
    "category": "hardcoded-secrets",
    "owasp": "A02",
    "cwe": "CWE-798",
    "severity": Severity.HIGH,
    "confidence": Confidence.HIGH,
    "title": "Potential hardcoded secret",
    "remediation": "Remove the secret from source control and load it from environment variables or a secrets manager.",
    "blocking_eligible": True,
}


def _severity_from_string(value: str | None) -> Severity:
    mapping = {
        "info": Severity.INFORMATIONAL,
        "low": Severity.LOW,
        "moderate": Severity.MEDIUM,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
        "critical": Severity.CRITICAL,
    }
    return mapping.get((value or "").lower(), Severity.HIGH)


def normalize_gitleaks(payload: Any, repo_root: Path) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    for item in payload or []:
        evidence = item.get("Secret") or item.get("Match")
        findings.append(
            ScanFinding(
                rule_id=item.get("RuleID", "gitleaks.generic"),
                category=GITLEAKS_RULE_METADATA["category"],
                owasp=GITLEAKS_RULE_METADATA["owasp"],
                cwe=GITLEAKS_RULE_METADATA["cwe"],
                severity=GITLEAKS_RULE_METADATA["severity"],
                confidence=GITLEAKS_RULE_METADATA["confidence"],
                title=item.get("Description") or GITLEAKS_RULE_METADATA["title"],
                message=item.get("Description") or "Potential hardcoded secret detected by gitleaks.",
                file_path=normalize_repo_path(item.get("File", ""), repo_root),
                line=item.get("StartLine"),
                tool="gitleaks",
                evidence=evidence,
                remediation=GITLEAKS_RULE_METADATA["remediation"],
                blocking_eligible=GITLEAKS_RULE_METADATA["blocking_eligible"],
            )
        )
    return findings


def normalize_semgrep(payload: dict[str, Any], repo_root: Path) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    for item in payload.get("results", []):
        rule_id = _canonical_semgrep_rule_id(item["check_id"])
        metadata = RULE_METADATA.get(rule_id, {})
        extra = item.get("extra", {})
        findings.append(
            ScanFinding(
                rule_id=rule_id,
                category=str(metadata.get("category", "custom-rule")),
                owasp=str(metadata.get("owasp", "")),
                cwe=metadata.get("cwe"),
                severity=metadata.get("severity", Severity.MEDIUM),
                confidence=metadata.get("confidence", Confidence.MEDIUM),
                title=str(metadata.get("title", extra.get("message", rule_id))),
                message=extra.get("message", rule_id),
                file_path=normalize_repo_path(item.get("path", ""), repo_root),
                line=(item.get("start") or {}).get("line"),
                tool="semgrep",
                evidence=extra.get("lines") or extra.get("message"),
                remediation=metadata.get("remediation"),
                blocking_eligible=bool(metadata.get("blocking_eligible", True)),
            )
        )
    return findings


def _canonical_semgrep_rule_id(rule_id: str) -> str:
    prefixes = ("github.semgrep.", "semgrep.")
    for prefix in prefixes:
        if rule_id.startswith(prefix):
            return rule_id[len(prefix):]
    return rule_id


def normalize_pip_audit(payload: dict[str, Any], repo_root: Path) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    for dependency in payload.get("dependencies", []):
        for vuln in dependency.get("vulns", []):
            aliases = vuln.get("aliases") or []
            advisory_id = vuln.get("id") or (aliases[0] if aliases else dependency["name"])
            severity = _severity_from_string(vuln.get("severity"))
            fix_versions = ", ".join(vuln.get("fix_versions") or [])
            description = vuln.get("description") or "Known vulnerable dependency detected by pip-audit."
            if fix_versions:
                description = f"{description} Fix versions: {fix_versions}."
            findings.append(
                ScanFinding(
                    rule_id=f"pip-audit:{advisory_id}",
                    category="vulnerable-dependencies",
                    owasp="A06",
                    cwe="CWE-1104",
                    severity=severity,
                    confidence=Confidence.HIGH,
                    title=f"Python dependency vulnerability in {dependency['name']}",
                    message=description,
                    file_path="backend/pyproject.toml",
                    line=None,
                    tool="pip-audit",
                    evidence=f"{dependency['name']} {dependency['version']}",
                    remediation="Upgrade the dependency to a fixed version and refresh the install state.",
                    blocking_eligible=True,
                    dependency_name=dependency["name"],
                    dependency_ecosystem="python",
                    dependency_version=dependency["version"],
                    advisory_id=advisory_id,
                )
            )
    return findings


def normalize_npm_audit(payload: dict[str, Any], repo_root: Path) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    vulnerabilities = payload.get("vulnerabilities", {})
    iterable = vulnerabilities.items() if isinstance(vulnerabilities, dict) else []

    for package_name, details in iterable:
        for via in details.get("via", []):
            if isinstance(via, str):
                advisory_id = via
                title = via
                severity = _severity_from_string(details.get("severity"))
                url = None
            else:
                advisory_id = via.get("source") or via.get("url") or via.get("name") or package_name
                title = via.get("title") or via.get("name") or f"Vulnerability in {package_name}"
                severity = _severity_from_string(via.get("severity") or details.get("severity"))
                url = via.get("url")

            message = title if not url else f"{title} ({url})"
            findings.append(
                ScanFinding(
                    rule_id=f"npm-audit:{advisory_id}",
                    category="vulnerable-dependencies",
                    owasp="A06",
                    cwe="CWE-1104",
                    severity=severity,
                    confidence=Confidence.HIGH,
                    title=f"Node dependency vulnerability in {package_name}",
                    message=message,
                    file_path="frontend/package-lock.json",
                    line=None,
                    tool="npm-audit",
                    evidence=f"{package_name} {details.get('range', '')}".strip(),
                    remediation="Upgrade the dependency to a fixed version and regenerate package-lock.json.",
                    blocking_eligible=True,
                    dependency_name=package_name,
                    dependency_ecosystem="npm",
                    dependency_version=details.get("range"),
                    advisory_id=str(advisory_id),
                )
            )
    return findings
