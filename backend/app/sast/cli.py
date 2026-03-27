from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from app.sast.base import ScanFinding, ScanSnapshot
from app.sast.diff_engine import DiffResult, compare_findings
from app.sast.normalize import (
    normalize_gitleaks,
    normalize_npm_audit,
    normalize_pip_audit,
    normalize_semgrep,
)
from app.sast.reporter import build_markdown_report, emit_github_annotations
from app.scanner.severity import Severity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR security scanner for VenomAI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan-snapshot", help="Run scanners and write normalized findings.")
    scan_parser.add_argument("--repo", required=True, help="Repository root to scan.")
    scan_parser.add_argument("--output", required=True, help="Path to normalized JSON output.")
    scan_parser.add_argument(
        "--diff-base",
        default=None,
        help="Git ref to diff against. When set, only files changed since this ref are scanned.",
    )
    scan_parser.add_argument(
        "--scope-root",
        action="append",
        default=[],
        help="Restrict scanning and normalized findings to this repo-relative path. May be provided multiple times.",
    )

    compare_parser = subparsers.add_parser("compare", help="Compare two snapshot JSON files.")
    compare_parser.add_argument("--base", required=True, help="Base snapshot JSON.")
    compare_parser.add_argument("--head", required=True, help="Head snapshot JSON.")
    compare_parser.add_argument("--markdown", required=True, help="Markdown summary output path.")
    compare_parser.add_argument("--json", required=True, help="Diff JSON output path.")
    compare_parser.add_argument(
        "--fail-threshold",
        default="high",
        choices=["informational", "low", "medium", "high", "critical"],
        help="Minimum severity that should fail the workflow.",
    )
    compare_parser.add_argument(
        "--github-annotations",
        action="store_true",
        help="Emit GitHub Actions annotations to stdout.",
    )

    args = parser.parse_args(argv)
    if args.command == "scan-snapshot":
        return scan_snapshot(
            Path(args.repo),
            Path(args.output),
            diff_base=args.diff_base,
            scope_roots=[Path(path) for path in args.scope_root],
        )
    if args.command == "compare":
        return compare_snapshots(
            Path(args.base),
            Path(args.head),
            Path(args.markdown),
            Path(args.json),
            Severity[args.fail_threshold.upper()],
            github_annotations=args.github_annotations,
        )
    return 1


def _get_changed_files(repo_root: Path, diff_base: str) -> list[str]:
    """Return repo-relative paths of files added, copied, modified, or renamed since *diff_base*."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{diff_base}...HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        # Fallback: try two-dot diff (works when merge-base can't be found)
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{diff_base}..HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]


def scan_snapshot(
    repo_root: Path,
    output_path: Path,
    *,
    diff_base: str | None = None,
    scope_roots: list[Path] | None = None,
) -> int:
    repo_root = repo_root.resolve()
    snapshot = ScanSnapshot(repo_root=str(repo_root))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_scope_roots = _normalize_scope_roots(repo_root, scope_roots or [])

    changed_files: list[str] | None = None
    if diff_base:
        changed_files = _get_changed_files(repo_root, diff_base)
        if normalized_scope_roots:
            changed_files = _filter_paths_by_scope(changed_files, normalized_scope_roots)
        if not changed_files:
            # Nothing changed in scope - write empty snapshot.
            output_path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
            return 0

    with tempfile.TemporaryDirectory(prefix="venomai-sast-") as tmpdir:
        temp_dir = Path(tmpdir)
        snapshot.findings.extend(
            _collect_tool_findings(
                repo_root,
                temp_dir,
                snapshot.tool_errors,
                changed_files,
                diff_base,
                normalized_scope_roots,
            )
        )

    output_path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return 0


def compare_snapshots(
    base_path: Path,
    head_path: Path,
    markdown_path: Path,
    json_path: Path,
    fail_threshold: Severity,
    github_annotations: bool = False,
) -> int:
    base_snapshot = ScanSnapshot.from_dict(json.loads(base_path.read_text(encoding="utf-8")))
    head_snapshot = ScanSnapshot.from_dict(json.loads(head_path.read_text(encoding="utf-8")))
    diff = compare_findings(base_snapshot.findings, head_snapshot.findings, fail_threshold)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(build_markdown_report(diff), encoding="utf-8")
    json_path.write_text(json.dumps(diff.to_dict(), indent=2), encoding="utf-8")

    if github_annotations:
        for annotation in emit_github_annotations(diff):
            print(annotation)

    if head_snapshot.tool_errors:
        print(f"Head snapshot tool errors: {head_snapshot.tool_errors}", file=sys.stderr)
    if base_snapshot.tool_errors:
        print(f"Base snapshot tool errors: {base_snapshot.tool_errors}", file=sys.stderr)

    return 1 if diff.blocking_findings else 0


# ---------------------------------------------------------------------------
# Tool runners
# ---------------------------------------------------------------------------

_PY_DEP_FILES = {"pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", "Pipfile.lock"}
_JS_DEP_FILES = {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
_IGNORED_FINDING_PATH_GLOBS = (
    "backend/semgrep_fixtures/**",
    "backend/tests/sast/test_normalize.py",
)


def _collect_tool_findings(
    repo_root: Path,
    temp_dir: Path,
    tool_errors: list[dict[str, str]],
    changed_files: list[str] | None,
    diff_base: str | None,
    scope_roots: list[str] | None = None,
) -> list[Any]:
    findings: list[Any] = []

    # Determine which tool groups are relevant based on changed files
    run_pip_audit = True
    run_npm_audit = True
    normalized_scope_roots = scope_roots or []

    if normalized_scope_roots:
        # Scoped scans are intended for sandbox code only.
        run_pip_audit = False
        run_npm_audit = False
    elif changed_files is not None:
        changed_basenames = {Path(f).name for f in changed_files}

        # Only run dep audits if their manifest files changed
        run_pip_audit = bool(changed_basenames & _PY_DEP_FILES)
        run_npm_audit = bool(changed_basenames & _JS_DEP_FILES)

    tasks: list[tuple[str, Any]] = [
        ("gitleaks", lambda: normalize_gitleaks(
            _run_gitleaks(repo_root, temp_dir / "gitleaks.json", diff_base=diff_base),
            repo_root,
        )),
        ("semgrep", lambda: normalize_semgrep(
            _run_semgrep(
                repo_root,
                temp_dir / "semgrep.json",
                changed_files=changed_files,
                scope_roots=normalized_scope_roots,
            ),
            repo_root,
        )),
    ]
    if run_pip_audit:
        tasks.append(("pip-audit", lambda: normalize_pip_audit(
            _run_pip_audit(repo_root, temp_dir / "pip-audit.json"), repo_root,
        )))
    if run_npm_audit:
        tasks.append(("npm-audit", lambda: normalize_npm_audit(
            _run_npm_audit(repo_root, temp_dir / "npm-audit.json"), repo_root,
        )))

    for tool_name, runner in tasks:
        try:
            tool_findings = runner()
            if normalized_scope_roots:
                tool_findings = _filter_findings_by_scope(tool_findings, normalized_scope_roots)
            if tool_name in {"gitleaks", "semgrep"}:
                tool_findings = _filter_ignored_findings(tool_findings)
            findings.extend(tool_findings)
        except Exception as exc:
            tool_errors.append({"tool": tool_name, "message": str(exc)})
    return findings


def _run_gitleaks(
    repo_root: Path,
    output_path: Path,
    *,
    diff_base: str | None = None,
) -> Any:
    _require_tool("gitleaks")

    if diff_base:
        # Scan only the commits in the diff range
        result = subprocess.run(
            [
                "gitleaks",
                "git",
                str(repo_root),
                "--log-opts",
                f"{diff_base}..HEAD",
                "--report-format",
                "json",
                "--report-path",
                str(output_path),
                "--exit-code",
                "0",
                "--no-banner",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    else:
        result = subprocess.run(
            [
                "gitleaks",
                "dir",
                str(repo_root),
                "--report-format",
                "json",
                "--report-path",
                str(output_path),
                "--exit-code",
                "0",
                "--no-banner",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gitleaks failed")
    return _read_json(output_path, [])


def _run_semgrep(
    repo_root: Path,
    output_path: Path,
    *,
    changed_files: list[str] | None = None,
    scope_roots: list[str] | None = None,
) -> dict[str, Any]:
    _require_tool("semgrep")
    config_path = repo_root / ".github" / "semgrep" / "agentic-pr.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Semgrep config not found: {config_path}")

    cmd = [
        "semgrep",
        "scan",
        "--config",
        str(config_path),
        "--no-git-ignore",
        "--json",
        "--output",
        str(output_path),
    ]

    if changed_files:
        # Scan only the changed files that still exist on disk
        existing = [
            str(repo_root / f)
            for f in changed_files
            if not _is_ignored_finding_path(f) and (repo_root / f).is_file()
        ]
        if not existing:
            return {"results": []}
        cmd.extend(existing)
    elif scope_roots:
        scoped_paths = [
            str(repo_root / scope_root)
            for scope_root in scope_roots
            if (repo_root / scope_root).exists()
        ]
        if not scoped_paths:
            return {"results": []}
        cmd.extend(scoped_paths)
    else:
        cmd.extend([
            "--exclude", ".git",
            "--exclude", ".venv",
            "--exclude", "frontend/node_modules",
            "--exclude", "frontend/.next",
            "--exclude", "backend/venomai_backend.egg-info",
            str(repo_root),
        ])

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "semgrep failed")
    return _read_json(output_path, {"results": []})


def _run_pip_audit(repo_root: Path, output_path: Path) -> dict[str, Any]:
    _require_tool("pip-audit")
    audit_result = subprocess.run(
        ["pip-audit", "--format", "json", "--output", str(output_path), str(repo_root / "backend")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if audit_result.returncode not in {0, 1}:
        raise RuntimeError(audit_result.stderr.strip() or audit_result.stdout.strip() or "pip-audit failed")
    return _read_json(output_path, {"dependencies": []})


def _run_npm_audit(repo_root: Path, output_path: Path) -> dict[str, Any]:
    _require_tool("npm")
    result = subprocess.run(
        ["npm", "audit", "--omit=dev", "--json"],
        cwd=repo_root / "frontend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "npm audit failed")
    output_path.write_text(result.stdout, encoding="utf-8")
    return json.loads(result.stdout or "{}")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    content = path.read_text(encoding="utf-8").strip()
    return json.loads(content) if content else default


def _filter_ignored_findings(findings: list[ScanFinding]) -> list[ScanFinding]:
    return [finding for finding in findings if not _is_ignored_finding_path(finding.file_path)]


def _filter_findings_by_scope(findings: list[ScanFinding], scope_roots: list[str]) -> list[ScanFinding]:
    return [finding for finding in findings if _is_in_scope(finding.file_path, scope_roots)]


def _filter_paths_by_scope(paths: list[str], scope_roots: list[str]) -> list[str]:
    return [path for path in paths if _is_in_scope(path, scope_roots)]


def _normalize_scope_roots(repo_root: Path, scope_roots: list[Path]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for scope_root in scope_roots:
        if scope_root.is_absolute():
            relative = scope_root.resolve().relative_to(repo_root)
        else:
            relative = scope_root
        normalized_path = relative.as_posix().strip("/")
        if not normalized_path or normalized_path == "." or normalized_path in seen:
            continue
        normalized.append(normalized_path)
        seen.add(normalized_path)
    return normalized


def _is_in_scope(path: str, scope_roots: list[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return any(
        normalized == scope_root or normalized.startswith(f"{scope_root}/")
        for scope_root in scope_roots
    )


def _is_ignored_finding_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    pure_path = PurePosixPath(normalized)
    return any(pure_path.match(pattern) for pattern in _IGNORED_FINDING_PATH_GLOBS)


def _require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise FileNotFoundError(f"Required tool not found on PATH: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
