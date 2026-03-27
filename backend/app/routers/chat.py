import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ChatMessage, Scan
from app.schemas import ChatMessageResponse, ChatRequest
from app.services.chat_service import stream_chat_response

router = APIRouter(prefix="/api/scans/{scan_id}/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def _format_sse(data: str, *, event: str | None = None) -> str:
    lines = data.split("\n")
    payload = []
    if event:
        payload.append(f"event: {event}")
    payload.extend(f"data: {line}" for line in lines)
    return "\n".join(payload) + "\n\n"


def _format_chat_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return "Chat request failed. Check the backend logs and ANTHROPIC_API_KEY."


@router.post("")
async def chat(
    scan_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != "completed":
        raise HTTPException(status_code=400, detail="Scan must be completed before chatting")

    async def event_stream():
        try:
            async for chunk in stream_chat_response(db, scan_id, body.message):
                yield _format_sse(chunk)
            yield _format_sse("[DONE]")
        except Exception as exc:
            logger.exception("Chat streaming failed for scan %s", scan_id)
            payload = json.dumps({"message": _format_chat_error(exc)})
            yield _format_sse(payload, event="error")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=list[ChatMessageResponse])
async def get_chat_history(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.scan_id == scan_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        ChatMessageResponse(
            id=m.id,
            scan_id=m.scan_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]
