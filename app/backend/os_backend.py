import asyncio, uuid, requests
from app.backend.pending_response_store import connected_os_clients, pending_responses
from app.api.android_api import incoming_data_queue
import time
from app.backend.logger import log



# ---------------- Base Dispatcher ---------------- #
class DeviceRouter:
    def __init__(self):
        self.windows_controller = WindowsController()
        self.android_controller = AndroidController()

    async def execute(self, os_device: str, function_name: str, arguments: dict) -> str:
        if os_device in ["pc", "laptop"]:
            return await self.windows_controller.execute(os_device, function_name, arguments)
        elif os_device in ["phone", "tab"]:
            return await self.android_controller.execute(os_device, function_name, arguments)
            # return f"❌ Android control is currently under development."

        else:
            return f"❌ Unsupported device: {os_device}"


# ---------------- Windows Controller ---------------- #
class WindowsController:
    async def execute(self, os_device: str, function_name: str, arguments: dict) -> str:
        ws = connected_os_clients.get(os_device)
        if not ws:
            return f"Device '{os_device}' is not connected."

        request_id = str(uuid.uuid4())
        data = {"request_id": request_id, "functionName": function_name, "arguments": arguments}

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        pending_responses[request_id] = future

        # Send to device
        await ws.send_json(data)

        try:
            response = await asyncio.wait_for(future, timeout=20)
            return f"[{os_device}] {response.get('result', 'No result')}"
        except asyncio.TimeoutError:
            pending_responses.pop(request_id, None)
            return f"Device '{os_device}' did not respond in time."
        except Exception as e:
            return f"Error receiving response from '{os_device}': {e}"


# ---------------- Android Controller ---------------- #
class AndroidController:
    def __init__(self):
        self.join_api_key = "eb3e0b7cc52d4acf95ecd77f5643f623"
        self.join_phone_id = "c6a07d0b1b9e470eb7181498d7eb8d49"
        self.join_tab_id = "8ee32ff238364678bf6ef90265a3c672"
        self.url = f"https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush"

    def percent_to_byte(self, percent: str, type: str) -> int:
        """Convert 0–100% to 0–255 scale."""
        percent = float(percent.strip('%')) # type: ignore
        percent = max(0, min(percent, 100))  # type: ignore # Clamp between 10–100
        if type == "brightness":
            return int(round((percent / 100) * 255)) # type: ignore
        else:
            return int(round((percent / 100) * 15)) # type: ignore



    async def execute(self, os_device: str, function_name: str, arguments: dict) -> str:
        if os_device == "phone":
            device_id = self.join_phone_id
        else:
            device_id = self.join_tab_id

        if function_name == "AppControl":
            params = {
                "apikey": self.join_api_key,
                "app": arguments.get("applicationName"),
                "deviceId": device_id
            }
        elif function_name == "WebsiteControl":
            params = {
                "apikey": self.join_api_key,
                "url": arguments.get("websiteUrl"),
                "deviceId": device_id
            }
        elif function_name == "SearchControl":
            search_platform = arguments.get("searchPlatform")
            search_content = arguments.get("searchContent", "").replace(" ", "+")
            if search_platform == "google":
                search_url = f"https://www.google.com/search?q={search_content}"
            else:
                search_url = f"https://www.youtube.com/results?search_query={search_content}"

            params = {
                "apikey": self.join_api_key,
                "url": search_url,
                "deviceId": device_id
            }
        
        elif function_name == "SystemControl":
            action = arguments.get("action")
            text = f"system control||{action}"
            params = {
                "apikey": self.join_api_key,
                "text": text,
                "deviceId": device_id
            }
        
        elif function_name == "DeviceInfo":
            info_type = arguments.get("informationType")
            text = f"info type||{info_type}"
            params = {
                "apikey": self.join_api_key,
                "text": text,
                "deviceId": device_id
            }
            # Send command to phone
            result = requests.get(self.url, params=params)
            try:
                if info_type == "location":
                    return_data = await asyncio.wait_for(incoming_data_queue.get(), timeout=10)
                    # log(f"[AndroidController] ✅ Received data: {return_data}")
                    return f"Phone {info_type}: {return_data}"
                else:
                    return "Ip address and internet speed fetching not implemented yet."
            except asyncio.TimeoutError:
                log("[AndroidController] ❌ Timeout waiting for phone response")
                return f"Timeout waiting for {info_type} from phone."
            
        elif function_name == "AdjustSettings":
            adjastment_type = arguments.get("adjustmentType")
            value_type = arguments.get("valueType")
            value = self.percent_to_byte(arguments.get("value"),value_type) # type: ignore

            text = f"{value_type}||{adjastment_type}||{value}"
            params = {
                "apikey": self.join_api_key,
                "text": text,
                "deviceId": device_id
            }
          
        
        else:
            return f"❌ Unsupported function '{function_name}' for Android."

        result = requests.get(self.url, params=params)
        return f"Sent '{function_name}' to {os_device}. Response: {result.text}"


if __name__ == "__main__":
    ac = AndroidController()
    log(asyncio.run(ac.execute('phone','SearchControl',{'searchContent':'cricket news','searchPlatform':'google'})))