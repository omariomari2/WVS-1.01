from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import Finding, Scan
from app.routers.findings import router


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _FakeSession:
    def __init__(self, scan: Scan, findings: list[Finding] | None = None):
        self.scan = scan
        self.findings = findings or []

    async def get(self, model, key):
        if model is Scan:
            return self.scan
        if model is Finding:
            return next((finding for finding in self.findings if finding.id == key), None)
        return None

    async def execute(self, query):
        return _FakeScalarResult(self.findings)


def _build_client(scan: Scan, findings: list[Finding] | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    session = _FakeSession(scan=scan, findings=findings)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_export_route_wins_over_dynamic_finding_route() -> None:
    scan = Scan(id="scan-1", target_url="https://example.com", status="completed")
    finding = Finding(
        id="finding-1",
        scan_id="scan-1",
        owasp_category="A01",
        owasp_name="Broken Access Control",
        severity="High",
        title="Admin page exposed",
        description="The admin page was reachable without authentication.",
        evidence="/admin returned HTTP 200",
        url="https://example.com/admin",
        remediation="Require authentication for administrative routes.",
        confidence="High",
        created_at="2026-03-25T00:00:00+00:00",
    )
    client = _build_client(scan, [finding])

    response = client.get("/api/scans/scan-1/findings/export/file?format=json")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="wvs_report.json"'
    payload = response.json()
    assert payload["target_url"] == "https://example.com"
    assert payload["findings"][0]["title"] == "Admin page exposed"


def test_export_rejects_scan_before_completion() -> None:
    client = _build_client(Scan(id="scan-1", target_url="https://example.com", status="running"))

    response = client.get("/api/scans/scan-1/findings/export/file?format=json")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Scan must finish successfully before findings can be exported."
    }
