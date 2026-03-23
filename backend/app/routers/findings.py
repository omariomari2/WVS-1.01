from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
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

    # Build severity summary (always from all findings, not filtered)
    all_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    all_findings = all_result.scalars().all()
    summary = Counter(f.severity for f in all_findings)

    return FindingsListResponse(
        findings=[_finding_to_response(f) for f in findings],
        summary=dict(summary),
    )


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
