from fastapi import APIRouter
from app.agent.assistant_initializer import assistant_manager
router = APIRouter(prefix="/sessions", tags=["Sessions"])

# Shared instance of MainAgentManager


@router.get("/")
def get_sessions():
    """List all active sessions."""
    return {"sessions": assistant_manager.session_manager.list_sessions()}


@router.delete("/{session_id}")
def clear_session(session_id: str):
    """Clear a specific session's memory."""
    success = assistant_manager.session_manager.clear_session(session_id)
    return {"success": success, "session_id": session_id}


@router.delete("/")
def clear_all_sessions():
    """Clear all sessions."""
    assistant_manager.session_manager.clear_all_sessions()
    return {"success": True}


@router.get("/state/{session_id}")
def get_state(session_id: str):
    """Get memory contents for a session (conversation + checkpoint state)."""
    config = {'configurable': {'thread_id': session_id}}
    state = assistant_manager.agent.get_state(config=config) # type: ignore
    return {"session_id": session_id, "state": state}

