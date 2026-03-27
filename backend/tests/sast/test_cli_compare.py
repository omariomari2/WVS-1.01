import json
from pathlib import Path

from app.sast.base import ScanFinding, ScanSnapshot
from app.sast.cli import compare_snapshots
from app.scanner.severity import Confidence, Severity


def test_compare_snapshots_writes_report_and_fails_on_new_blocking_issue(tmp_path: Path) -> None:
    base_snapshot = ScanSnapshot(repo_root="repo", findings=[])
    head_snapshot = ScanSnapshot(
        repo_root="repo",
        findings=[
            ScanFinding(
                rule_id="venomai.hardcoded-secrets.python.assignment",
                category="hardcoded-secrets",
                owasp="A02",
                cwe="CWE-798",
                severity=Severity.HIGH,
                confidence=Confidence.HIGH,
                title="Hardcoded secret assignment",
                message="Suspicious hardcoded secret assigned in Python code.",
                file_path="backend/app/config.py",
                line=12,
                tool="semgrep",
                evidence='API_KEY = "sk_live_123"',
                remediation="Use environment variables.",
                blocking_eligible=True,
            )
        ],
    )

    base_path = tmp_path / "base.json"
    head_path = tmp_path / "head.json"
    markdown_path = tmp_path / "summary.md"
    diff_path = tmp_path / "diff.json"
    base_path.write_text(json.dumps(base_snapshot.to_dict()), encoding="utf-8")
    head_path.write_text(json.dumps(head_snapshot.to_dict()), encoding="utf-8")

    exit_code = compare_snapshots(base_path, head_path, markdown_path, diff_path, Severity.HIGH)

    assert exit_code == 1
    assert "New blocking findings" in markdown_path.read_text(encoding="utf-8")
    diff_payload = json.loads(diff_path.read_text(encoding="utf-8"))
    assert diff_payload["counts"]["blocking"] == 1
