import json
from collections import defaultdict

from fastapi import WebSocket


class ScanProgressManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, scan_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[scan_id].append(websocket)

    def disconnect(self, scan_id: str, websocket: WebSocket):
        self._connections[scan_id].remove(websocket)
        if not self._connections[scan_id]:
            del self._connections[scan_id]

    async def broadcast(self, scan_id: str, data: dict):
        message = json.dumps(data)
        dead = []
        for ws in self._connections.get(scan_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self._connections[scan_id].remove(ws)
            except ValueError:
                pass


progress_manager = ScanProgressManager()
