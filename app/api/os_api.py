from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid, json
from app.backend.pending_response_store import connected_os_clients, pending_responses
from app.backend.logger import log



router = APIRouter(prefix="/ws")

@router.websocket("/os_client/{device_id}")
async def os_client_ws(ws: WebSocket, device_id: str):
    await ws.accept()
    connected_os_clients[device_id] = ws
    log(f"✅ Device connected: {device_id}")

    try:
        while True:
            msg = await ws.receive_json()
            log(f"[{device_id}] -> {msg}")  

            # If it's a response with request_id, resolve the future
            if "request_id" in msg:
                request_id = msg["request_id"]
                future = pending_responses.pop(request_id, None)
                if future:
                    future.set_result(msg)

    except WebSocketDisconnect:
        log(f"❌ Device disconnected: {device_id}")
        connected_os_clients.pop(device_id, None)
