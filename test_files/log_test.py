import asyncio
import websockets

LOG_SERVER_URL = "ws://api.shuun.site/ws/logs"  # Change if deployed remotely
# LOG_SERVER_URL = "ws://127.0.0.1:8001/ws/logs"  # Change if deployed remotely


async def listen_logs():
    print(f"📡 Connecting to log server at {LOG_SERVER_URL} ...")
    try:
        async with websockets.connect(LOG_SERVER_URL) as ws:
            print("✅ Connected! Listening for logs...\n")
            async for message in ws:
                print(f"[LOG] {message}")
    except websockets.exceptions.ConnectionClosedError:
        print("❌ Connection closed by server.")
    except ConnectionRefusedError:
        print("🚫 Could not connect to log server. Is it running?")
    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    asyncio.run(listen_logs())
