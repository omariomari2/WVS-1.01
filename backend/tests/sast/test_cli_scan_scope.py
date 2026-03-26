from pathlib import Path

from app.sast import cli


def test_changed_file_scan_skips_dependency_audits_without_manifest_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    temp_dir = tmp_path / "temp"
    repo_root.mkdir()
    temp_dir.mkdir()

    called: list[str] = []

    monkeypatch.setattr(cli, "_run_gitleaks", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_semgrep", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_pip_audit", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_npm_audit", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "normalize_gitleaks", lambda raw, repo_root: called.append("gitleaks") or [])
    monkeypatch.setattr(cli, "normalize_semgrep", lambda raw, repo_root: called.append("semgrep") or [])
    monkeypatch.setattr(cli, "normalize_pip_audit", lambda raw, repo_root: called.append("pip-audit") or [])
    monkeypatch.setattr(cli, "normalize_npm_audit", lambda raw, repo_root: called.append("npm-audit") or [])

    findings = cli._collect_tool_findings(
        repo_root,
        temp_dir,
        tool_errors=[],
        changed_files=["backend/app/main.py", "frontend/src/app/page.tsx"],
        diff_base="base-sha",
    )

    assert findings == []
    assert called == ["gitleaks", "semgrep"]


def test_changed_file_scan_runs_dependency_audits_for_manifest_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    temp_dir = tmp_path / "temp"
    repo_root.mkdir()
    temp_dir.mkdir()

    called: list[str] = []

    monkeypatch.setattr(cli, "_run_gitleaks", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_semgrep", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_pip_audit", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_npm_audit", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "normalize_gitleaks", lambda raw, repo_root: called.append("gitleaks") or [])
    monkeypatch.setattr(cli, "normalize_semgrep", lambda raw, repo_root: called.append("semgrep") or [])
    monkeypatch.setattr(cli, "normalize_pip_audit", lambda raw, repo_root: called.append("pip-audit") or [])
    monkeypatch.setattr(cli, "normalize_npm_audit", lambda raw, repo_root: called.append("npm-audit") or [])

    findings = cli._collect_tool_findings(
        repo_root,
        temp_dir,
        tool_errors=[],
        changed_files=["backend/requirements.txt", "frontend/package-lock.json"],
        diff_base="base-sha",
    )

    assert findings == []
    assert called == ["gitleaks", "semgrep", "pip-audit", "npm-audit"]
