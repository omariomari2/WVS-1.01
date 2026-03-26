import csv
import io
import json
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Finding, Scan
from app.schemas import FindingResponse, FindingsListResponse

router = APIRouter(prefix="/api/scans/{scan_id}/findings", tags=["findings"])


@router.get("", response_model=FindingsListResponse)
async def get_findings(
    scan_id: str,
    severity: str | None = Query(None),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    query = select(Finding).where(Finding.scan_id == scan_id)
    if severity:
        query = query.where(Finding.severity == severity)
    if category:
        query = query.where(Finding.owasp_category == category)

    query = query.order_by(Finding.created_at)
    result = await db.execute(query)
    findings = result.scalars().all()

    all_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    all_findings = all_result.scalars().all()
    summary = Counter(f.severity for f in all_findings)

    return FindingsListResponse(
        findings=[_finding_to_response(f) for f in findings],
        summary=dict(summary),
    )


@router.get("/export/file")
async def export_findings(
    scan_id: str,
    format: str = Query(..., pattern="^(json|csv|pdf)$"),
    db: AsyncSession = Depends(get_db),
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Scan must finish successfully before findings can be exported.",
        )

    result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id).order_by(Finding.created_at)
    )
    findings = result.scalars().all()
    rows = [_finding_to_dict(f) for f in findings]

    if format == "json":
        return _export_json(rows, scan.target_url)
    if format == "csv":
        return _export_csv(rows)
    return _export_pdf(rows, scan.target_url)


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    scan_id: str,
    finding_id: str,
    db: AsyncSession = Depends(get_db),
):
    finding = await db.get(Finding, finding_id)
    if not finding or finding.scan_id != scan_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return _finding_to_response(finding)


SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Informational": 4}

_FIELDS = [
    "severity", "owasp_category", "owasp_name", "title",
    "description", "evidence", "url", "remediation", "confidence", "created_at",
]


def _finding_to_dict(f: Finding) -> dict:
    return {
        "severity": f.severity,
        "owasp_category": f.owasp_category,
        "owasp_name": f.owasp_name,
        "title": f.title,
        "description": f.description,
        "evidence": f.evidence or "",
        "url": f.url,
        "remediation": f.remediation,
        "confidence": f.confidence,
        "created_at": f.created_at,
    }


def _export_json(rows: list[dict], target_url: str) -> StreamingResponse:
    payload = json.dumps({"target_url": target_url, "findings": rows}, indent=2)
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="findings.json"'},
    )


def _export_csv(rows: list[dict]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="findings.csv"'},
    )


def _export_pdf(rows: list[dict], target_url: str) -> StreamingResponse:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "VenomAI Security Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Target: {target_url}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 8, f"Total findings: {len(rows)}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    from collections import Counter as _Ctr
    counts = _Ctr(r["severity"] for r in rows)
    summary_parts = [f"{sev}: {counts.get(sev, 0)}" for sev in SEVERITY_ORDER]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "  |  ".join(summary_parts), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    sorted_rows = sorted(rows, key=lambda r: SEVERITY_ORDER.get(r["severity"], 99))

    sev_colors = {
        "Critical": (220, 38, 38), "High": (234, 88, 12),
        "Medium": (202, 138, 4), "Low": (22, 163, 74), "Informational": (59, 130, 246),
    }

    for i, row in enumerate(sorted_rows, 1):
        if pdf.get_y() > 250:
            pdf.add_page()

        r, g, b = sev_colors.get(row["severity"], (100, 100, 100))
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(28, 7, f" {row['severity']}", fill=True)
        pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"  {i}. {row['title']}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, f"{row['owasp_category']} - {row['owasp_name']}  |  Confidence: {row['confidence']}  |  URL: {row['url']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, row["description"], new_x="LMARGIN", new_y="NEXT")

        if row["evidence"]:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 4, f"Evidence: {row['evidence']}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "Remediation:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, row["remediation"], new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="findings.pdf"'},
    )


def _finding_to_response(f: Finding) -> FindingResponse:
    return FindingResponse(
        id=f.id,
        scan_id=f.scan_id,
        owasp_category=f.owasp_category,
        owasp_name=f.owasp_name,
        severity=f.severity,
        title=f.title,
        description=f.description,
        evidence=f.evidence,
        url=f.url,
        remediation=f.remediation,
        confidence=f.confidence,
        created_at=f.created_at,
    )
