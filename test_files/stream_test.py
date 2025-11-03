import asyncio
import websockets
import json
import os
import time

QUERIES_FILE = "queries.txt"
WS_URI = "ws://api.shuun.site/ws/chat_stream"
RETRY_DELAY = 5  # seconds between reconnect attempts


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
    """Listens for streamed tokens and final messages from the backend."""
    try:
        async for message in ws:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"\n🤖 Bot (raw): {message}")
                continue

            msg_type = data.get("type")

            if msg_type == "stream":
                token = data.get("token", "")
                print(token, end="", flush=True)

            elif msg_type == "end":
                print("\n✅ Response complete.")

            elif data.get("error"):
                print(f"\n❌ Error: {data['error']}")

            else:
                print(f"\n🤖 Bot: {data}")

    except websockets.ConnectionClosed as e:
        print(f"\n🔌 Connection closed: {e}")
        raise  # Let outer loop handle reconnection
    except Exception as e:
        print(f"\n⚠️ Receiver error: {e}")
        raise


async def connect_forever():
    """Keeps the websocket connection alive, reconnecting on failure."""
    while True:
        try:
            print(f"🔗 Connecting to {WS_URI} ...")
            async with websockets.connect(WS_URI) as ws:
                print("🤖 Connected to chatbot (streaming enabled).")
                print("💡 Type messages into queries.txt — each new line sends automatically.\n")

                # Run sender and receiver concurrently
                await asyncio.gather(sender(ws), receiver(ws))

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"\n⚠️ Connection lost or failed: {e}")
            print(f"⏳ Retrying in {RETRY_DELAY} seconds...\n")
            await asyncio.sleep(RETRY_DELAY)
        except KeyboardInterrupt:
            print("👋 Closed by user.")
            return
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print(f"⏳ Retrying in {RETRY_DELAY} seconds...\n")
            await asyncio.sleep(RETRY_DELAY)


if __name__ == "__main__":
    try:
        asyncio.run(connect_forever())
    except KeyboardInterrupt:
        print("👋 Program terminated by user.")
