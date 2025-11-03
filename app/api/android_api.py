from fastapi import Request
# from app.agent.assistant_initializer import incoming_data_queue
from fastapi import APIRouter
import asyncio
from app.backend.logger import log


incoming_data_queue = asyncio.Queue()

router = APIRouter()

# This could be a queue where your brain loop reads data

@router.post("/from_phone")
async def from_phone(request: Request):
    data = await request.json()
    # log("Received from phone:", data, flush=True)
    await incoming_data_queue.put(data)
    return {"status": "ok", "received": data}
