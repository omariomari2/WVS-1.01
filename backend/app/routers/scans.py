import asyncio

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Scan
from app.schemas import ScanCreate, ScanResponse
from app.services.scan_orchestrator import run_scan
from app.websocket.scan_progress import progress_manager

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(
    body: ScanCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if not body.authorization_confirmed:
        raise HTTPException(
            status_code=403,
            detail="You must confirm that you are authorized to scan this target.",
        )

    target_url = str(body.target_url).rstrip("/")

    # Validate URL is reachable
    try:
        async with httpx.AsyncClient(timeout=5, verify=False) as client:
            resp = await client.head(target_url, follow_redirects=True)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot reach target URL: {e}",
        )

    scan = Scan(target_url=target_url)
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Launch scan in background
    background_tasks.add_task(run_scan, scan.id, target_url)

    return _scan_to_response(scan)


@router.get("", response_model=list[ScanResponse])
async def list_scans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()))
    scans = result.scalars().all()
    return [_scan_to_response(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_to_response(scan)


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    await db.delete(scan)
    await db.commit()


def _scan_to_response(scan: Scan) -> ScanResponse:
    return ScanResponse(
        id=scan.id,
        target_url=scan.target_url,
        status=scan.status,
        progress=scan.progress,
        current_module=scan.current_module,
        total_findings=scan.total_findings,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        error_message=scan.error_message,
    )
