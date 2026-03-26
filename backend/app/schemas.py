from pydantic import BaseModel, HttpUrl


class ScanCreate(BaseModel):
    target_url: HttpUrl
    authorization_confirmed: bool


class PrScanCreate(BaseModel):
    pr_url: str


class ScanResponse(BaseModel):
    id: str
    target_url: str
    status: str
    progress: float
    current_module: str | None
    total_findings: int
    created_at: str
    completed_at: str | None
    error_message: str | None
    scan_type: str = "url"
    pr_url: str | None = None
    pr_number: int | None = None
    repo_owner: str | None = None
    repo_name: str | None = None
    pr_title: str | None = None
    pr_branch: str | None = None
    base_branch: str | None = None
    head_sha: str | None = None
    local_repo_path: str | None = None


class FindingResponse(BaseModel):
    id: str
    scan_id: str
    owasp_category: str
    owasp_name: str
    severity: str
    title: str
    description: str
    evidence: str | None
    url: str
    remediation: str
    confidence: str
    created_at: str
    file_path: str | None = None
    line_number: int | None = None
    commit_sha: str | None = None
    code_snippet: str | None = None
    diff_hunk: str | None = None
    rule_id: str | None = None
    cwe: str | None = None


class FindingsListResponse(BaseModel):
    findings: list[FindingResponse]
    summary: dict[str, int]


class PrCommitResponse(BaseModel):
    id: str
    scan_id: str
    sha: str
    message: str
    author: str
    created_at: str


class RectifyRequest(BaseModel):
    finding_id: str


class RectifyManualCommentRequest(BaseModel):
    finding_id: str
    comment: str


class RectifyResponse(BaseModel):
    success: bool
    action: str
    finding_id: str
    content: str | None = None
    diff_preview: str | None = None
    message: str | None = None


class ChatRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    id: str
    scan_id: str
    role: str
    content: str
    created_at: str
