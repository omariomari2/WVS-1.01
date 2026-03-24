from app.sast.base import ScanFinding
from app.sast.diff_engine import compare_findings
from app.scanner.severity import Confidence, Severity


def _finding(**overrides) -> ScanFinding:
    payload = {
        "rule_id": "venomai.sql-injection.python.execute-string",
        "category": "sql-injection",
        "owasp": "A03",
        "cwe": "CWE-89",
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "SQL query built with string interpolation",
        "message": "Unsafe SQL execution.",
        "file_path": "backend/app/example.py",
        "line": 10,
        "tool": "semgrep",
        "evidence": 'cursor.execute(f"SELECT {user_input}")',
        "remediation": "Use parameters.",
        "blocking_eligible": True,
    }
    payload.update(overrides)
    return ScanFinding(**payload)


def test_same_issue_with_line_movement_is_unchanged() -> None:
    base = _finding(line=10)
    head = _finding(line=88)

    diff = compare_findings([base], [head], Severity.HIGH)

    assert not diff.new_findings
    assert not diff.resolved_findings
    assert len(diff.unchanged_findings) == 1


def test_dependency_findings_match_by_package_and_advisory() -> None:
    base = _finding(
        rule_id="pip-audit:PYSEC-2024-1",
        category="vulnerable-dependencies",
        owasp="A06",
        cwe="CWE-1104",
        severity=Severity.HIGH,
        title="Python dependency vulnerability in requests",
        message="Known vulnerable dependency.",
        file_path="backend/pyproject.toml",
        line=None,
        tool="pip-audit",
        evidence="requests 2.0.0",
        dependency_name="requests",
        dependency_ecosystem="python",
        dependency_version="2.0.0",
        advisory_id="PYSEC-2024-1",
    )
    head = _finding(
        rule_id="pip-audit:PYSEC-2024-1",
        category="vulnerable-dependencies",
        owasp="A06",
        cwe="CWE-1104",
        severity=Severity.HIGH,
        title="Python dependency vulnerability in requests",
        message="Known vulnerable dependency.",
        file_path="backend/pyproject.toml",
        line=None,
        tool="pip-audit",
        evidence="requests 2.0.0",
        dependency_name="requests",
        dependency_ecosystem="python",
        dependency_version="2.0.0",
        advisory_id="PYSEC-2024-1",
    )

    diff = compare_findings([base], [head], Severity.HIGH)

    assert not diff.new_findings
    assert not diff.resolved_findings
    assert len(diff.unchanged_findings) == 1


def test_changed_dependency_advisory_is_new() -> None:
    base = _finding(
        rule_id="npm-audit:100",
        category="vulnerable-dependencies",
        owasp="A06",
        cwe="CWE-1104",
        severity=Severity.HIGH,
        title="Node dependency vulnerability in next",
        message="Old advisory.",
        file_path="frontend/package-lock.json",
        line=None,
        tool="npm-audit",
        evidence="next < 15.0.2",
        dependency_name="next",
        dependency_ecosystem="npm",
        dependency_version="< 15.0.2",
        advisory_id="100",
    )
    head = _finding(
        rule_id="npm-audit:101",
        category="vulnerable-dependencies",
        owasp="A06",
        cwe="CWE-1104",
        severity=Severity.HIGH,
        title="Node dependency vulnerability in next",
        message="New advisory.",
        file_path="frontend/package-lock.json",
        line=None,
        tool="npm-audit",
        evidence="next < 15.0.3",
        dependency_name="next",
        dependency_ecosystem="npm",
        dependency_version="< 15.0.3",
        advisory_id="101",
    )

    diff = compare_findings([base], [head], Severity.HIGH)

    assert len(diff.new_findings) == 1
    assert len(diff.resolved_findings) == 1


def test_advisory_only_findings_do_not_block() -> None:
    advisory = _finding(
        rule_id="venomai.missing-authorization.fastapi.route",
        category="missing-authorization",
        severity=Severity.HIGH,
        confidence=Confidence.LOW,
        blocking_eligible=False,
    )

    diff = compare_findings([], [advisory], Severity.HIGH)

    assert len(diff.new_findings) == 1
    assert not diff.blocking_findings
