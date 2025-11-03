from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, sessions, os_api, chat_stream, android_api, log_stream
import uvicorn, sys, asyncio, io
from app.backend import log_broadcaster
from app.backend.logger import log

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# Fix Proactor loop issue on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(
    title="Nandi AI Assistant API",
    description="AI Assistant with LangGraph Framework and React Agent Architecture",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def start_broadcaster():
    asyncio.create_task(log_broadcaster.run())
    print("📡 Log broadcaster started")

# Routers
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(os_api.router)
app.include_router(chat_stream.router)
app.include_router(android_api.router)
app.include_router(log_stream.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Nandi AI Assistant API",
        "version": "1.0",
        "endpoints": {
            "chat (WebSocket)": "/ws/chat",
            "sessions": "GET /sessions - Get active sessions",
            "clear_session": "DELETE /sessions/{session_id} - Clear specific session",
            "clear_all": "DELETE /sessions - Clear all sessions",
            "state": "GET /sessions/state/{session_id} - Get memory contents"
        }
    }


if __name__ == "__main__":
    log("🚀 Starting OM AI Assistant API Server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
