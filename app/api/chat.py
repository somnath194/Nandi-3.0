from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect
from datetime import datetime
from app.backend.schemas import AssistantResponse
from app.agent.assistant_initializer import assistant_manager
from app.backend.logger import log


router = APIRouter(prefix="/ws")


@router.websocket("/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            query = data.get("query")
            session_id = data.get("session_id", "default")

            if not query:
                await ws.send_json({
                    "error": "Query cannot be empty",
                    "timestamp": datetime.now().isoformat()
                })
                continue

            response_text = await assistant_manager.invoke(query, session_id)

            response_model = AssistantResponse(
                response=response_text,
                timestamp=datetime.now().isoformat(),
                session_id=session_id
            )
            await ws.send_json(jsonable_encoder(response_model))
            

    except WebSocketDisconnect:
        log("🔌 WebSocket disconnected")
    except Exception as e:
        log(f"❌ WebSocket error: {e}")
        await ws.send_json({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
