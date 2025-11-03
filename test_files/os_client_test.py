import websockets
import json, asyncio

async def main():
    uri = "ws://127.0.0.1:8001/ws/os_client/pc"  # Change if your server runs elsewhere
    async with websockets.connect(uri) as ws:
        print("🤖 Connected to OS client (type 'exit' to quit)\n")

        try:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                print(f"\n🟢 OS Client: {data}")

                await asyncio.sleep(1)  # slight delay to avoid busy waiting

                await ws.send(json.dumps({
                    "request_id": data.get("request_id", "unknown"),
                    "result": "Command received and executed successfully."
                }))

        except websockets.ConnectionClosed as e:
            print(f"🔌 Connection closed: {e}")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Exiting...")