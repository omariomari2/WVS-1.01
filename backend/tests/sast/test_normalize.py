from pathlib import Path

from app.sast.normalize import normalize_gitleaks, normalize_npm_audit, normalize_pip_audit, normalize_semgrep


def test_normalize_semgrep_uses_rule_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path
    payload = {
        "results": [
            {
                "check_id": "github.semgrep.venomai.sql-injection.python.execute-string",
                "path": str(repo_root / "backend" / "app" / "example.py"),
                "start": {"line": 14},
                "extra": {
                    "message": "SQL appears to be assembled with string interpolation before execution.",
                    "lines": 'cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")',
                },
            }
        ]
    }

    findings = normalize_semgrep(payload, repo_root)

    assert len(findings) == 1
    assert findings[0].category == "sql-injection"
    assert findings[0].file_path == "backend/app/example.py"
    assert findings[0].owasp == "A03"


def test_normalize_gitleaks_produces_high_confidence_secret_finding(tmp_path: Path) -> None:
    repo_root = tmp_path
    payload = [
        {
            "RuleID": "generic-api-key",
            "Description": "Generic API Key",
            "File": str(repo_root / "backend" / "app" / "config.py"),
            "StartLine": 8,
            "Secret": "sk_live_1234567890",
        }
    ]

    findings = normalize_gitleaks(payload, repo_root)

    assert findings[0].category == "hardcoded-secrets"
    assert findings[0].line == 8
    assert findings[0].tool == "gitleaks"


def test_normalize_pip_audit_uses_dependency_fingerprint_fields(tmp_path: Path) -> None:
    findings = normalize_pip_audit(
        {
            "dependencies": [
                {
                    "name": "jinja2",
                    "version": "3.0.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2024-10",
                            "fix_versions": ["3.1.4"],
                            "aliases": ["CVE-2024-0001"],
                            "description": "Template injection issue.",
                        }
                    ],
                }
            ]
        },
        tmp_path,
    )

    assert findings[0].dependency_name == "jinja2"
    assert findings[0].dependency_ecosystem == "python"
    assert findings[0].advisory_id == "PYSEC-2024-10"


def test_normalize_npm_audit_handles_nested_via_entries(tmp_path: Path) -> None:
    findings = normalize_npm_audit(
        {
            "vulnerabilities": {
                "next": {
                    "range": "<15.0.2",
                    "severity": "high",
                    "via": [
                        {
                            "source": 1234,
                            "title": "Server-side request forgery",
                            "severity": "high",
                            "url": "https://example.com/advisories/1234",
                        }
                    ],
                }
            }
        },
        tmp_path,
    )

    assert findings[0].dependency_name == "next"
    assert findings[0].dependency_ecosystem == "npm"
    assert findings[0].rule_id == "npm-audit:1234"
