from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from datetime import datetime
from app.agent.assistant_initializer import assistant_manager
from app.backend.logger import log


router = APIRouter(prefix="/ws")

@router.websocket("/chat_stream")
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

            main_agent_run_id = None
            final_response = None

            async for event in assistant_manager.invoke_stream(query, session_id):
                event_type = event.get("event")
                event_data = event.get("data", {})
                
                # --- Identify the Main Agent (OM) by its system prompt ---
                if event_type == "on_chat_model_start":
                    input_data = event_data.get("input", {})
                    messages = input_data.get("messages", [[]])[0]
                    
                    # Check if this is the Main Agent "OM"
                    for msg in messages:
                        content = getattr(msg, "content", "")
                        if "You are OM, the main helpful AI Assistant" in str(content):
                            # Extract the run_id from the subsequent stream events
                            # We'll set it when we see the first stream event
                            main_agent_run_id = "PENDING"
                            break

                # --- Stream tokens ONLY from the Main Agent ---
                elif event_type == "on_chat_model_stream":
                    chunk = event_data.get("chunk", {})
                    chunk_id = getattr(chunk, "id", "")
                    token = getattr(chunk, "content", "") or ""
                    
                    # Set the main agent run_id from the first stream event after "PENDING"
                    if main_agent_run_id == "PENDING" and chunk_id:
                        main_agent_run_id = chunk_id
                    
                    # Only stream if this chunk is from the main agent
                    if token and chunk_id == main_agent_run_id:
                        await ws.send_json({"type": "stream", "token": token})

                # --- Capture the final response (always the last one) ---
                elif event_type == "on_chat_model_end":
                    output = event_data.get("output")
                    if output and getattr(output, "content", ""):
                        final_response = output.content.strip()

            # Send the final response
            if final_response:
                await ws.send_json({
                    "type": "end",
                    "response": final_response,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                })

    except WebSocketDisconnect:
        log("🔌 WebSocket disconnected")

    except Exception as e:
        log(f"❌ WebSocket error: {e}")
        await ws.send_json({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
