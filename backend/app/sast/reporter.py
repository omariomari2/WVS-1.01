from __future__ import annotations

from app.sast.base import SEVERITY_ORDER, ScanFinding
from app.sast.diff_engine import DiffResult


def build_markdown_report(diff: DiffResult) -> str:
    advisory = [finding for finding in diff.new_findings if finding not in diff.blocking_findings]
    dependency_changes = [
        finding for finding in diff.new_findings + diff.resolved_findings if finding.is_dependency_finding
    ]

    lines = [
        "# PR Security Summary",
        "",
        f"- New blocking findings: {len(diff.blocking_findings)}",
        f"- New advisory findings: {len(advisory)}",
        f"- Resolved findings: {len(diff.resolved_findings)}",
        f"- Unchanged findings suppressed: {len(diff.unchanged_findings)}",
        "",
    ]
    lines.extend(_section("New blocking findings", diff.blocking_findings))
    lines.extend(_section("New advisory findings", advisory))
    lines.extend(_section("Resolved findings", diff.resolved_findings))
    lines.extend(_section("Dependency changes", dependency_changes))
    return "\n".join(lines).rstrip() + "\n"


def emit_github_annotations(diff: DiffResult) -> list[str]:
    annotations: list[str] = []
    for finding in diff.new_findings:
        level = "error" if finding in diff.blocking_findings else "warning"
        annotations.append(
            f"::{level} file={finding.file_path or '.'},line={finding.line or 1},"
            f"title={_escape(finding.title)}::{_escape(f'{finding.message} [{finding.category}]')}"
        )
    return annotations


def _section(title: str, findings: list[ScanFinding]) -> list[str]:
    lines = [f"## {title}", ""]
    if not findings:
        lines.extend(["_None_", ""])
        return lines

    for finding in sorted(findings, key=_sort_key):
        location = finding.file_path
        if finding.line:
            location = f"{location}:{finding.line}"
        lines.append(f"- [{finding.severity.value}] {finding.title} in `{location}`")
        lines.append(f"  - {finding.message}")
        if finding.remediation:
            lines.append(f"  - Remediation: {finding.remediation}")
    lines.append("")
    return lines


def _sort_key(finding: ScanFinding) -> tuple[int, str, int]:
    return (-SEVERITY_ORDER[finding.severity], finding.file_path, finding.line or 0)


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
