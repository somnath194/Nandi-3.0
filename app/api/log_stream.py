from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from app.backend import log_broadcaster

router = APIRouter(prefix="/ws")

@router.websocket("/logs")
async def websocket_logs(ws: WebSocket):
    await ws.accept()
    await log_broadcaster.register(ws)

    try:
        while True:
            await ws.receive_text()  # Keep alive (ignore any input)
    except WebSocketDisconnect:
        await log_broadcaster.unregister(ws)
