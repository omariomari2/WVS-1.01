from pathlib import Path
import json

from app.sast import cli
from app.sast.base import ScanFinding
from app.scanner.severity import Confidence, Severity


def _finding(file_path: str, *, tool: str = "semgrep") -> ScanFinding:
    return ScanFinding(
        rule_id="venomai.test.rule",
        category="test-category",
        owasp="A03",
        cwe="CWE-89",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        title="Test finding",
        message="Synthetic finding for scan scope tests.",
        file_path=file_path,
        line=1,
        tool=tool,
        blocking_eligible=True,
    )


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


def test_changed_file_scan_filters_intentional_fixture_findings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    temp_dir = tmp_path / "temp"
    repo_root.mkdir()
    temp_dir.mkdir()

    monkeypatch.setattr(cli, "_run_gitleaks", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_semgrep", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        cli,
        "normalize_gitleaks",
        lambda raw, repo_root: [_finding("backend/tests/sast/test_normalize.py", tool="gitleaks")],
    )
    monkeypatch.setattr(
        cli,
        "normalize_semgrep",
        lambda raw, repo_root: [
            _finding("backend/semgrep_fixtures/unsafe_python.py"),
            _finding("backend/app/main.py"),
        ],
    )

    findings = cli._collect_tool_findings(
        repo_root,
        temp_dir,
        tool_errors=[],
        changed_files=["backend/app/main.py"],
        diff_base="base-sha",
    )

    assert [finding.file_path for finding in findings] == ["backend/app/main.py"]


def test_run_pip_audit_targets_backend_project_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    backend_dir = repo_root / "backend"
    output_path = tmp_path / "pip-audit.json"
    backend_dir.mkdir(parents=True)

    commands: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        output_path.write_text(json.dumps({"dependencies": []}), encoding="utf-8")
        return _Result()

    monkeypatch.setattr(cli, "_require_tool", lambda name: None)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    payload = cli._run_pip_audit(repo_root, output_path)

    assert payload == {"dependencies": []}
    assert commands == [[
        "pip-audit",
        "--format",
        "json",
        "--output",
        str(output_path),
        str(backend_dir),
    ]]


def test_scoped_scan_skips_dependency_audits_even_when_manifest_changes(
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
        changed_files=["sandbox/project-a/package.json", "sandbox/project-a/requirements.txt"],
        diff_base="base-sha",
        scope_roots=["sandbox/project-a"],
    )

    assert findings == []
    assert called == ["gitleaks", "semgrep"]


def test_scoped_scan_filters_findings_to_requested_roots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    temp_dir = tmp_path / "temp"
    repo_root.mkdir()
    temp_dir.mkdir()

    monkeypatch.setattr(cli, "_run_gitleaks", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_run_semgrep", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        cli,
        "normalize_gitleaks",
        lambda raw, repo_root: [
            _finding("sandbox/project-a/config.py", tool="gitleaks"),
            _finding("sandbox/project-b/secret.txt", tool="gitleaks"),
        ],
    )
    monkeypatch.setattr(
        cli,
        "normalize_semgrep",
        lambda raw, repo_root: [
            _finding("sandbox/project-a/app.py"),
            _finding("sandbox/project-c/app.py"),
        ],
    )

    findings = cli._collect_tool_findings(
        repo_root,
        temp_dir,
        tool_errors=[],
        changed_files=["sandbox/project-a/app.py", "sandbox/project-b/secret.txt", "sandbox/project-c/app.py"],
        diff_base="base-sha",
        scope_roots=["sandbox/project-a", "sandbox/project-c"],
    )

    assert [finding.file_path for finding in findings] == [
        "sandbox/project-a/config.py",
        "sandbox/project-a/app.py",
        "sandbox/project-c/app.py",
    ]


def test_scan_snapshot_writes_empty_snapshot_when_scope_filters_out_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    output_path = tmp_path / "snapshot.json"
    repo_root.mkdir()

    monkeypatch.setattr(cli, "_get_changed_files", lambda repo_root, diff_base: ["backend/app/main.py"])
    monkeypatch.setattr(
        cli,
        "_collect_tool_findings",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not collect findings")),
    )

    exit_code = cli.scan_snapshot(
        repo_root,
        output_path,
        diff_base="base-sha",
        scope_roots=[Path("sandbox/project-a")],
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload == {"repo_root": str(repo_root.resolve()), "findings": [], "tool_errors": []}


def test_run_semgrep_without_diff_base_scans_only_scope_roots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    output_path = tmp_path / "semgrep.json"
    scoped_dir = repo_root / "sandbox" / "project-a"
    other_dir = repo_root / "sandbox" / "project-b"
    config_path = repo_root / ".github" / "semgrep"
    scoped_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)
    config_path.mkdir(parents=True)
    (config_path / "agentic-pr.yml").write_text("rules: []", encoding="utf-8")

    commands: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        output_path.write_text(json.dumps({"results": []}), encoding="utf-8")
        return _Result()

    monkeypatch.setattr(cli, "_require_tool", lambda name: None)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    payload = cli._run_semgrep(
        repo_root,
        output_path,
        scope_roots=["sandbox/project-a"],
    )

    assert payload == {"results": []}
    assert commands == [[
        "semgrep",
        "scan",
        "--config",
        str(config_path / "agentic-pr.yml"),
        "--no-git-ignore",
        "--json",
        "--output",
        str(output_path),
        str(scoped_dir),
    ]]
