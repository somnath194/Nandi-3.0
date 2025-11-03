import asyncio
from app.backend import log_broadcaster

def log(message: str):
    """Print to console + broadcast to WebSocket clients."""
    print(message)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(log_broadcaster.log(message))
    except RuntimeError:
        pass  # if called during startup before loop is ready
