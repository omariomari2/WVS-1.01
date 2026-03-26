from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PrCommit, Scan
from app.schemas import PrCommitResponse, PrScanCreate, ScanResponse
from app.services.github_client import parse_pr_url
from app.services.local_repo import resolve_repo_path
from app.services.pr_ingest import run_pr_ingest

router = APIRouter(prefix="/api/pr-scans", tags=["pr-scans"])


@router.post("", response_model=ScanResponse, status_code=201)
async def create_pr_scan(
    body: PrScanCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        owner, repo_name, pr_number = parse_pr_url(body.pr_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo_path = resolve_repo_path(repo_name)

    scan = Scan(
        target_url=body.pr_url,
        scan_type="pr",
        pr_url=body.pr_url,
        pr_number=pr_number,
        repo_owner=owner,
        repo_name=repo_name,
        local_repo_path=str(repo_path) if repo_path else None,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    background_tasks.add_task(run_pr_ingest, scan.id, body.pr_url)

    return _scan_response(scan)


@router.get("", response_model=list[ScanResponse])
async def list_pr_scans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scan).where(Scan.scan_type == "pr").order_by(Scan.created_at.desc())
    )
    return [_scan_response(s) for s in result.scalars().all()]


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_pr_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan = await db.get(Scan, scan_id)
    if not scan or scan.scan_type != "pr":
        raise HTTPException(status_code=404, detail="PR scan not found")
    return _scan_response(scan)


@router.get("/{scan_id}/commits", response_model=list[PrCommitResponse])
async def get_pr_commits(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan = await db.get(Scan, scan_id)
    if not scan or scan.scan_type != "pr":
        raise HTTPException(status_code=404, detail="PR scan not found")

    result = await db.execute(
        select(PrCommit).where(PrCommit.scan_id == scan_id).order_by(PrCommit.created_at)
    )
    commits = result.scalars().all()
    return [
        PrCommitResponse(
            id=c.id, scan_id=c.scan_id, sha=c.sha,
            message=c.message, author=c.author, created_at=c.created_at,
        )
        for c in commits
    ]


def _scan_response(scan: Scan) -> ScanResponse:
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
        scan_type=scan.scan_type,
        pr_url=scan.pr_url,
        pr_number=scan.pr_number,
        repo_owner=scan.repo_owner,
        repo_name=scan.repo_name,
        pr_title=scan.pr_title,
        pr_branch=scan.pr_branch,
        base_branch=scan.base_branch,
        head_sha=scan.head_sha,
        local_repo_path=scan.local_repo_path,
    )
