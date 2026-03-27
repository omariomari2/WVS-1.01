from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.scanner.severity import Confidence, Severity


SEVERITY_ORDER = {
    Severity.INFORMATIONAL: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def _parse_severity(value: str | Severity) -> Severity:
    if isinstance(value, Severity):
        return value

    normalized = value.strip().lower()
    for severity in Severity:
        if severity.value.lower() == normalized or severity.name.lower() == normalized:
            return severity
    raise ValueError(f"Unsupported severity value: {value}")


def _parse_confidence(value: str | Confidence) -> Confidence:
    if isinstance(value, Confidence):
        return value

    normalized = value.strip().lower()
    for confidence in Confidence:
        if confidence.value.lower() == normalized or confidence.name.lower() == normalized:
            return confidence
    raise ValueError(f"Unsupported confidence value: {value}")


def normalize_repo_path(path: str, repo_root: Path) -> str:
    raw_path = Path(path)
    if raw_path.is_absolute():
        normalized = raw_path.resolve().relative_to(repo_root.resolve())
    else:
        normalized = raw_path
    return normalized.as_posix()


def severity_meets_threshold(severity: Severity, threshold: Severity) -> bool:
    return SEVERITY_ORDER[severity] >= SEVERITY_ORDER[threshold]


@dataclass(slots=True)
class ScanFinding:
    rule_id: str
    category: str
    owasp: str
    cwe: str | None
    severity: Severity
    confidence: Confidence
    title: str
    message: str
    file_path: str
    line: int | None
    tool: str
    evidence: str | None = None
    remediation: str | None = None
    fingerprint: str | None = None
    blocking_eligible: bool = True
    dependency_name: str | None = None
    dependency_ecosystem: str | None = None
    dependency_version: str | None = None
    advisory_id: str | None = None

    def __post_init__(self) -> None:
        self.severity = _parse_severity(self.severity)
        self.confidence = _parse_confidence(self.confidence)
        self.file_path = self.file_path.replace("\\", "/")
        if self.fingerprint is None:
            self.fingerprint = self.compute_fingerprint()

    @property
    def is_dependency_finding(self) -> bool:
        return self.tool in {"pip-audit", "npm-audit"} or self.category == "vulnerable-dependencies"

    def compute_fingerprint(self) -> str:
        if self.is_dependency_finding:
            basis = "|".join([
                self.tool,
                self.dependency_ecosystem or "",
                self.dependency_name or "",
                self.advisory_id or self.rule_id,
                self.dependency_version or "",
            ])
        else:
            basis = "|".join([
                self.tool,
                self.rule_id,
                self.file_path,
                (self.evidence or self.message or "").strip(),
            ])
        return sha256(basis.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["confidence"] = self.confidence.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScanFinding":
        return cls(**payload)


@dataclass(slots=True)
class ScanSnapshot:
    repo_root: str
    findings: list[ScanFinding] = field(default_factory=list)
    tool_errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": self.repo_root,
            "findings": [finding.to_dict() for finding in self.findings],
            "tool_errors": list(self.tool_errors),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScanSnapshot":
        return cls(
            repo_root=payload["repo_root"],
            findings=[ScanFinding.from_dict(item) for item in payload.get("findings", [])],
            tool_errors=list(payload.get("tool_errors", [])),
        )
