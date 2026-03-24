from __future__ import annotations

from dataclasses import dataclass

from app.sast.base import SEVERITY_ORDER, ScanFinding, severity_meets_threshold
from app.scanner.severity import Severity


@dataclass(slots=True)
class DiffResult:
    new_findings: list[ScanFinding]
    resolved_findings: list[ScanFinding]
    unchanged_findings: list[ScanFinding]
    blocking_findings: list[ScanFinding]

    def to_dict(self) -> dict[str, object]:
        return {
            "new_findings": [finding.to_dict() for finding in self.new_findings],
            "resolved_findings": [finding.to_dict() for finding in self.resolved_findings],
            "unchanged_findings": [finding.to_dict() for finding in self.unchanged_findings],
            "blocking_findings": [finding.to_dict() for finding in self.blocking_findings],
            "counts": {
                "new": len(self.new_findings),
                "resolved": len(self.resolved_findings),
                "unchanged": len(self.unchanged_findings),
                "blocking": len(self.blocking_findings),
            },
        }


def compare_findings(
    base_findings: list[ScanFinding],
    head_findings: list[ScanFinding],
    fail_threshold: Severity,
) -> DiffResult:
    base_by_fingerprint = {finding.fingerprint: finding for finding in base_findings}
    head_by_fingerprint = {finding.fingerprint: finding for finding in head_findings}

    new_keys = set(head_by_fingerprint) - set(base_by_fingerprint)
    resolved_keys = set(base_by_fingerprint) - set(head_by_fingerprint)
    unchanged_keys = set(base_by_fingerprint) & set(head_by_fingerprint)

    new_findings = [head_by_fingerprint[key] for key in new_keys]
    resolved_findings = [base_by_fingerprint[key] for key in resolved_keys]
    unchanged_findings = [head_by_fingerprint[key] for key in unchanged_keys]
    blocking_findings = [
        finding
        for finding in new_findings
        if finding.blocking_eligible and severity_meets_threshold(finding.severity, fail_threshold)
    ]

    return DiffResult(
        new_findings=sorted(new_findings, key=_sort_key),
        resolved_findings=sorted(resolved_findings, key=_sort_key),
        unchanged_findings=sorted(unchanged_findings, key=_sort_key),
        blocking_findings=sorted(blocking_findings, key=_sort_key),
    )


def _sort_key(finding: ScanFinding) -> tuple[int, str, int]:
    return (-SEVERITY_ORDER[finding.severity], finding.file_path, finding.line or 0)
