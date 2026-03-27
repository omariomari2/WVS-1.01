from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Finding, Scan
from app.schemas import RectifyManualCommentRequest, RectifyRequest, RectifyResponse
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


@router.post("/claude", response_model=RectifyResponse)
async def send_to_claude(
    scan_id: str,
    body: RectifyRequest,
    db: AsyncSession = Depends(get_db),
):
    scan, finding = await _get_scan_and_finding(scan_id, body.finding_id, db)
    result = await rectify_service.send_to_claude(db, scan, finding)
    return RectifyResponse(**result)


@router.post("/comment/ai", response_model=RectifyResponse)
async def pr_comment_ai(
    scan_id: str,
    body: RectifyRequest,
    db: AsyncSession = Depends(get_db),
):
    scan, finding = await _get_scan_and_finding(scan_id, body.finding_id, db)
    result = await rectify_service.pr_comment_ai(db, scan, finding)
    return RectifyResponse(**result)


@router.post("/comment/manual", response_model=RectifyResponse)
async def pr_comment_manual(
    scan_id: str,
    body: RectifyManualCommentRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="Comment cannot be empty.")

    scan, finding = await _get_scan_and_finding(scan_id, body.finding_id, db)
    result = await rectify_service.pr_comment_manual(db, scan, finding, body.comment)
    return RectifyResponse(**result)
