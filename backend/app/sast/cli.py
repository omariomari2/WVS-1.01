from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.sast.base import ScanSnapshot
from app.sast.diff_engine import compare_findings
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
        return scan_snapshot(Path(args.repo), Path(args.output))
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


def scan_snapshot(repo_root: Path, output_path: Path) -> int:
    repo_root = repo_root.resolve()
    snapshot = ScanSnapshot(repo_root=str(repo_root))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="venomai-sast-") as tmpdir:
        temp_dir = Path(tmpdir)
        snapshot.findings.extend(_collect_tool_findings(repo_root, temp_dir, snapshot.tool_errors))

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


def _collect_tool_findings(
    repo_root: Path,
    temp_dir: Path,
    tool_errors: list[dict[str, str]],
) -> list[Any]:
    findings = []
    tasks = [
        ("gitleaks", lambda: normalize_gitleaks(_run_gitleaks(repo_root, temp_dir / "gitleaks.json"), repo_root)),
        ("semgrep", lambda: normalize_semgrep(_run_semgrep(repo_root, temp_dir / "semgrep.json"), repo_root)),
        ("pip-audit", lambda: normalize_pip_audit(_run_pip_audit(repo_root, temp_dir / "pip-audit.json"), repo_root)),
        ("npm-audit", lambda: normalize_npm_audit(_run_npm_audit(repo_root, temp_dir / "npm-audit.json"), repo_root)),
    ]

    for tool_name, runner in tasks:
        try:
            findings.extend(runner())
        except Exception as exc:
            tool_errors.append({"tool": tool_name, "message": str(exc)})
    return findings


def _run_gitleaks(repo_root: Path, output_path: Path) -> Any:
    _require_tool("gitleaks")
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


def _run_semgrep(repo_root: Path, output_path: Path) -> dict[str, Any]:
    _require_tool("semgrep")
    config_path = repo_root / ".github" / "semgrep" / "agentic-pr.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Semgrep config not found: {config_path}")

    result = subprocess.run(
        [
            "semgrep",
            "scan",
            "--config",
            str(config_path),
            "--no-git-ignore",
            "--json",
            "--output",
            str(output_path),
            "--exclude",
            ".git",
            "--exclude",
            ".venv",
            "--exclude",
            "frontend/node_modules",
            "--exclude",
            "frontend/.next",
            "--exclude",
            "backend/venomai_backend.egg-info",
            str(repo_root),
        ],
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
    python_executable = sys.executable

    install_result = subprocess.run(
        [python_executable, "-m", "pip", "install", "-e", str(repo_root / "backend")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if install_result.returncode != 0:
        raise RuntimeError(install_result.stderr.strip() or install_result.stdout.strip() or "backend install failed")

    audit_result = subprocess.run(
        ["pip-audit", "--format", "json", "--output", str(output_path)],
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


def _require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise FileNotFoundError(f"Required tool not found on PATH: {name}")


if __name__ == "__main__":
    raise SystemExit(main())
