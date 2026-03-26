from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Finding, Scan
from app.schemas import RectifyBatchRequest, RectifyRequest, RectifyResponse
from app.services import rectify_service

router = APIRouter(prefix="/api/pr-scans/{scan_id}/rectify", tags=["rectify"])


async def _get_scan_and_finding(
    scan_id: str, finding_id: str, db: AsyncSession
) -> tuple[Scan, Finding]:
    scan = await db.get(Scan, scan_id)
    if not scan or scan.scan_type != "pr":
        raise HTTPException(status_code=404, detail="PR scan not found")
    finding = await db.get(Finding, finding_id)
    if not finding or finding.scan_id != scan_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return scan, finding


@router.post("/send", response_model=RectifyResponse)
async def send_to_cursor(
    scan_id: str,
    body: RectifyRequest,
    db: AsyncSession = Depends(get_db),
):
    scan, finding = await _get_scan_and_finding(scan_id, body.finding_id, db)
    result = await rectify_service.send_to_cursor(db, scan, finding)
    return RectifyResponse(**result)


@router.post("/apply", response_model=RectifyResponse)
async def apply_fix(
    scan_id: str,
    body: RectifyRequest,
    db: AsyncSession = Depends(get_db),
):
    scan, finding = await _get_scan_and_finding(scan_id, body.finding_id, db)
    result = await rectify_service.apply_fix(db, scan, finding)
    return RectifyResponse(**result)


@router.post("/comment", response_model=RectifyResponse)
async def pr_comment(
    scan_id: str,
    body: RectifyRequest,
    db: AsyncSession = Depends(get_db),
):
    scan, finding = await _get_scan_and_finding(scan_id, body.finding_id, db)
    result = await rectify_service.pr_comment(db, scan, finding)
    return RectifyResponse(**result)


@router.post("/review", response_model=RectifyResponse)
async def full_review(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
):
    scan = await db.get(Scan, scan_id)
    if not scan or scan.scan_type != "pr":
        raise HTTPException(status_code=404, detail="PR scan not found")

    result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = list(result.scalars().all())
    if not findings:
        raise HTTPException(status_code=400, detail="No findings to review")

    review_result = await rectify_service.full_review(db, scan, findings)
    return RectifyResponse(**review_result)


@router.post("/batch", response_model=list[RectifyResponse])
async def batch_rectify(
    scan_id: str,
    body: RectifyBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    scan = await db.get(Scan, scan_id)
    if not scan or scan.scan_type != "pr":
        raise HTTPException(status_code=404, detail="PR scan not found")

    if body.action not in ("send", "apply", "comment"):
        raise HTTPException(status_code=400, detail="Invalid batch action")

    results = []
    for finding_id in body.finding_ids:
        finding = await db.get(Finding, finding_id)
        if not finding or finding.scan_id != scan_id:
            results.append(RectifyResponse(
                success=False, action=body.action,
                finding_id=finding_id, message="Finding not found",
            ))
            continue

        action_map = {
            "send": rectify_service.send_to_cursor,
            "apply": rectify_service.apply_fix,
            "comment": rectify_service.pr_comment,
        }
        result = await action_map[body.action](db, scan, finding)
        results.append(RectifyResponse(**result))

    return results
