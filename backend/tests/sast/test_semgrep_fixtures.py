import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("semgrep") is None, reason="semgrep is not installed")
def test_semgrep_fixture_scan_detects_vulnerable_patterns() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    fixture_dir = repo_root / "backend" / "semgrep_fixtures"
    config_path = repo_root / ".github" / "semgrep" / "agentic-pr.yml"

    result = subprocess.run(
        [
            "semgrep",
            "scan",
            "--config",
            str(config_path),
            "--no-git-ignore",
            "--json",
            str(fixture_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode in {0, 1}, result.stderr
    payload = json.loads(result.stdout)
    rule_ids = {item["check_id"] for item in payload.get("results", [])}
    safe_paths = {
        Path(item["path"]).name
        for item in payload.get("results", [])
        if Path(item["path"]).name.startswith("safe_")
    }

    assert any(rule_id.endswith("venomai.hardcoded-secrets.python.assignment") for rule_id in rule_ids)
    assert any(rule_id.endswith("venomai.sql-injection.python.execute-string") for rule_id in rule_ids)
    assert any(rule_id.endswith("venomai.insecure-defaults.python.verify-disabled") for rule_id in rule_ids)
    assert any(rule_id.endswith("venomai.command-injection.python.shell-true") for rule_id in rule_ids)
    assert any(rule_id.endswith("venomai.xss.react.dangerous-html") for rule_id in rule_ids)
    assert not safe_paths
