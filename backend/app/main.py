from contextlib import asynccontextmanager
from pathlib import Path
import json
import uuid
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import chat, findings, scans
from app.websocket.scan_progress import progress_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    matching_routes = [
        str(route.path)
        for route in app.routes
        if "findings" in str(route.path) and "export/file" in str(route.path)
    ]
    #region agent log startup_export_routes
    payload = {
        "sessionId": "c10438",
        "runId": "initial",
        "hypothesisId": "H1_route_missing",
        "location": "backend/app/main.py:lifespan_route_registration",
        "message": "registered findings export routes",
        "data": {"matching_routes": matching_routes},
        "timestamp": int(time.time() * 1000),
        "id": f"dbg_{uuid.uuid4()}",
    }
    log_path = Path(__file__).resolve().parents[2] / "debug-c10438.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False))
        f.write("\n")
    #endregion agent log startup_export_routes
    yield


app = FastAPI(
    title="VenomAI",
    description="OWASP Top 10 Web Security Scanner",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scans.router)
app.include_router(findings.router)
app.include_router(chat.router)


@app.websocket("/ws/scans/{scan_id}")
async def scan_progress_ws(websocket: WebSocket, scan_id: str):
    await progress_manager.connect(scan_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_manager.disconnect(scan_id, websocket)


@app.get("/api/health")
async def health():
    return {"status": "ok"}

