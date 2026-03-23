from pydantic import BaseModel, HttpUrl


class ScanCreate(BaseModel):
    target_url: HttpUrl
    authorization_confirmed: bool


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


class FindingsListResponse(BaseModel):
    findings: list[FindingResponse]
    summary: dict[str, int]


class ChatRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    id: str
    scan_id: str
    role: str
    content: str
    created_at: str
