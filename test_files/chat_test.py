import asyncio
import websockets
import json
import os

QUERIES_FILE = "queries.txt"

async def sender(ws):
    """Reads queries from a text file and sends them to the websocket."""
    print(f"📂 Watching {QUERIES_FILE} for queries... (edit this file to send messages)")
    seen = set()

    while True:
        if os.path.exists(QUERIES_FILE):
            with open(QUERIES_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            for line in lines:
                if line not in seen:
                    seen.add(line)

                    if line.lower() == "exit":
                        print("👋 Exiting...")
                        await ws.close()
                        return
                    payload = {
                        "query": line,
                        "session_id": "test-session"
                    }

                    await ws.send(json.dumps(payload))
                    print(f"\n🟢 You (from file): {line}")

        await asyncio.sleep(2)  # check file every 2 seconds

async def receiver(ws):
    """Always listens for messages from the backend and prints them."""
    try:
        async for response in ws:
            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                print(f"\n🤖 Bot (raw): {response}")
                continue

            print(f"\n🤖 Bot: {data.get('response')}")
           
    except websockets.ConnectionClosed as e:
        print(f"🔌 Connection closed: {e}")

async def main():
    # uri = "ws://api.shuun.site/ws/chat"
    uri = "ws://localhost:8001/ws/chat"          # Change if your server runs elsewhere
    async with websockets.connect(uri) as ws:
        print("🤖 Connected to chatbot (queries come from queries.txt)\n")

        await asyncio.gather(
            sender(ws),
            receiver(ws)
        )

if __name__ == "__main__":
    asyncio.run(main())
