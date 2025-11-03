import asyncio

class LogBroadcaster:
    """Async log broadcaster for WebSocket clients."""
    def __init__(self):
        self.clients = set()
        self.queue = asyncio.Queue()

    async def register(self, ws):
        self.clients.add(ws)
        print(f"📡 New log client connected ({len(self.clients)} total)")

    async def unregister(self, ws):
        self.clients.remove(ws)
        print(f"❌ Log client disconnected ({len(self.clients)} total)")

    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSocket clients."""
        if not self.clients:
            return
        disconnected = []
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            await self.unregister(ws)

    async def log(self, message: str):
        """Queue and broadcast log messages."""
        await self.queue.put(message)

    async def run(self):
        """Continuously broadcast queued logs."""
        while True:
            msg = await self.queue.get()
            await self.broadcast(msg)
