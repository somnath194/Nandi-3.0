import paho.mqtt.client as paho
import asyncio
import time
from datetime import datetime
# from app.core.logs import logs_push
import aiohttp,ast
from typing import List, Dict, Any
from app.backend.logger import log


class HomeController:
    def __init__(self, mqtt_server="broker.mqtt.cool"):
        self.client = paho.Client(paho.CallbackAPIVersion.VERSION2) # type: ignore
        self.mqtt_server = mqtt_server

        self.topic_map = {
            "bedroom": "somn194_control/bedroom_appliance",
            "outside": "somn194_control/outside_appliance",
            "work": "somn194_control/work_appliance"
        }

        self.device_relay_map = {
            "bedroom light":     ("bedroom", "relay1"),
            "bedroom fan":       ("bedroom", "relay4"),
            "bedroom bulb":      ("bedroom", "relay3"),
            "side led":          ("bedroom", "relay2"),

            "bathroom light":    ("outside", "relay3"),
            "stair light":        ("outside", "relay1"),
            "outdoor light":     ("outside", "relay2"),
            "outdoor camera":    ("outside", "relay4"),

            "main led":          ("work", "relay1"),
            "pc":                ("work", "relay2"),
            "home theater":      ("work", "relay3"),
            "soldering iron":    ("work", "relay4"),
            "raspberry pi":      ("work", "relay5")
        }

        self.blocked_off = {"pc", "raspberry pi"}

    async def mqtt_publish(self, command, topic):
        await asyncio.to_thread(self._publish_sync, command, topic)

    def _publish_sync(self, command, topic):
        try:
            result = self.client.connect(self.mqtt_server, 1883, 60)
            if result == 0:
                self.client.publish(topic, command, 0)
                time.sleep(1)
        except Exception as e:
            log(f"❌ MQTT error: {e}")

    async def appliance_control(self, controlled_appliance: str, controlled_state: str) -> str:
        """
        Controls a appliance by sending an MQTT message.

        :param controlled_appliance: The name of the appliance to control (e.g., 'bedroom light', 'pc', 'fan).
        :param controlled_state: The desired state: 'on' or 'off'.
        :return: A success or failure message.
        """
        controlled_appliance = controlled_appliance.lower()
        controlled_state = controlled_state.lower()

        if controlled_appliance not in self.device_relay_map:
            return f"Unknown device: {controlled_appliance}. Available devices: {list(self.device_relay_map.keys())}"
            
        if controlled_state not in ["on", "off"]:
            return f"Invalid state '{controlled_state}'. Must be 'on' or 'off'."


        topic_key, relay_id = self.device_relay_map[controlled_appliance]
        topic = self.topic_map[topic_key]

        # Handle special case: restricted OFF permission
        if controlled_state == "off" and controlled_appliance in self.blocked_off:
            return f"I don't have permission to turn off {controlled_appliance.title()}! I will not take action."

        command = f"{relay_id}_{controlled_state}"
        
        # Publish the message
        await self.mqtt_publish(command, topic)
        
        return f"Successfully sent command to turn {controlled_state} {controlled_appliance}."


class LEDStripController:
    def __init__(self):
        self.WLED_IP = "192.168.1.5"
        self.BACK_WLED_IP = "192.168.1.6"

        self.DEVICE_MAP = {
            "192.168.1.5" : "main",
            "192.168.1.6" : "back"
        }
        self.SEGMENT_MAP = {
            "front almary": 1,
            "behind the money plant": 2,
            "ceiling": 3,
            "under laptop table": 4,
            "under pc table": 5,
            "ganesha almary": 6,
            "shiva almary": 7,
            "all": 8,
            "back almary": 9
        }

    async def send_wled_request(self, payload: Dict[str, Any], ip: str) -> Dict[str, Any]:
        """Send payload to WLED device and return structured result with device name + ip."""
        device_name = self.DEVICE_MAP[ip]
        url = f"http://{ip}/json/state"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    text = await resp.text()
                    if resp.status == 200:
                        return {
                            "device": device_name,
                            "ip": ip,
                            "ok": True,
                            "status": resp.status,
                            "body": text
                        }
                    return {
                        "device": device_name,
                        "ip": ip,
                        "ok": False,
                        "status": resp.status,
                        "body": text
                    }
        except Exception as e:
            return {
                "device": device_name,
                "ip": ip,
                "ok": False,
                "status": None,
                "error": f"Cannot connect to {device_name} LED strip light ({ip}): {str(e)}"
            }
               
    def _normalize_rgb(self, rgb) -> (List[int], List[str]): # type: ignore
        """Return normalized rgb list [r,g,b] and warnings list (if any)."""
        warnings: List[str] = []
        if isinstance(rgb, str):
            try:
                rgb = ast.literal_eval(rgb)
            except Exception:
                warnings.append("Invalid RGB string format. Using [0,0,0].")
                return [0, 0, 0], warnings

        if not isinstance(rgb, (list, tuple)) or len(rgb) != 3:
            warnings.append("rgb_colour_code must be a list of three integers. Using [0,0,0].")
            return [0, 0, 0], warnings

        normalized = []
        for v in rgb:
            try:
                vi = int(v)
            except Exception:
                vi = 0
                warnings.append(f"RGB value '{v}' could not be parsed, using 0.")
            vi = max(0, min(255, vi))
            normalized.append(vi)

        return normalized, warnings

    def _clamp_brightness(self, bri: int) -> (int, List[str]): # type: ignore
        warnings: List[str] = []
        try:
            bri_i = int(bri)
        except Exception:
            warnings.append("Invalid brightness value. Using default 150.")
            return 150, warnings
        if bri_i < 0:
            warnings.append("Brightness below 0 set to 0.")
            bri_i = 0
        if bri_i > 255:
            warnings.append("Brightness above 255 set to 255.")
            bri_i = 255
        return bri_i, warnings

    async def set_led_segment(self, segment_name: str, rgb_colour_code, brightness_value: int = 150) -> Dict[str, Any]:
        """
        Set color/brightness of a specific LED strip segment or all segments.
        Returns structured result with status, message and per-IP details.
        """
        result: Dict[str, Any] = {
            "status": "error",
            "message": "",
            "segment": segment_name,
            "segment_id": None,
            "warnings": [],
            "details": []
        }

        if not isinstance(segment_name, str):
            result["message"] = "segment_name must be a string."
            return result

        segment_id = self.SEGMENT_MAP.get(segment_name.lower())
        result["segment_id"] = segment_id

        rgb_normalized, rgb_warnings = self._normalize_rgb(rgb_colour_code)
        bri_clamped, bri_warnings = self._clamp_brightness(brightness_value)
        result["warnings"].extend(rgb_warnings)
        result["warnings"].extend(bri_warnings)

        if segment_id is None:
            result["message"] = f"Unknown segment: '{segment_name}'. No action taken."
            return result

        # Build payload(s) depending on segment
        if segment_id == 8:  # 'all' -> apply to main WLED (per segment) and back WLED (id 0)
            payload_main = {"on": True, "bri": bri_clamped, "ps": -1, "seg": []}
            for name, sid in self.SEGMENT_MAP.items():
                if sid in (8, 9):
                    continue
                payload_main["seg"].append({
                    "id": sid,
                    "col": [rgb_normalized, [0, 0, 0], [0, 0, 0]],
                    "bri": bri_clamped
                })
            resp_main = await self.send_wled_request(payload_main, self.WLED_IP)
            result["details"].append(resp_main)

            payload_back = {
                "on": True,
                "bri": bri_clamped,
                "seg": [{
                    "id": 0,
                    "col": [rgb_normalized, [0, 0, 0], [0, 0, 0]]
                }]
            }
            resp_back = await self.send_wled_request(payload_back, self.BACK_WLED_IP)
            result["details"].append(resp_back)

            ok_any = any(d.get("ok") for d in result["details"])
            result["status"] = "success" if ok_any else "error"
            result["message"] = "Applied color to ALL segments." if ok_any else "Failed to apply color to ALL segments."
            return result

        elif segment_id == 9:  # back almary -> send only to BACK_WLED_IP
            payload = {
                "on": True,
                "bri": bri_clamped,
                "seg": [{
                    "id": 0,
                    "col": [rgb_normalized, [0, 0, 0], [0, 0, 0]]
                }]
            }
            resp = await self.send_wled_request(payload, self.BACK_WLED_IP)
            result["details"].append(resp)
            result["status"] = "success" if resp.get("ok") else "error"
            result["message"] = f"Applied color to segment '{segment_name}'." if resp.get("ok") else f"Failed to apply color to segment '{segment_name}'."
            if not resp.get("ok") and resp.get("error"):
                result["warnings"].append(resp.get("error"))
            return result

        else:  # single segment on main WLED
            payload = {"on": True, "bri": bri_clamped, "ps": -1, "seg": [{
                "id": segment_id,
                "col": [rgb_normalized, [0, 0, 0], [0, 0, 0]],
                "bri": bri_clamped
            }]}
            resp = await self.send_wled_request(payload, self.WLED_IP)
            result["details"].append(resp)
            result["status"] = "success" if resp.get("ok") else "error"
            result["message"] = f"Applied color to segment '{segment_name}'." if resp.get("ok") else f"Failed to apply color to segment '{segment_name}'."
            if not resp.get("ok") and resp.get("error"):
                result["warnings"].append(resp.get("error"))
            return result

    async def set_segment_mode(self, strip_mode: str) -> Dict[str, Any]:
        """
        Set a predefined effect/mode for the LED strip.
        Returns structured result with status, message and details.
        """
        result: Dict[str, Any] = {
            "status": "error",
            "message": "",
            "strip_mode": strip_mode,
            "warnings": [],
            "details": []
        }

        payload = None
        mode = (strip_mode or "").strip()

        if mode == "musicSync":
            payload = {
                "on": True,
                "bri": 200,
                "ps": -1,
                "seg": [{
                    "id": 0,
                    "on": True,
                    "bri": 255,
                    "col": [[255, 255, 255], [0, 0, 0], [0, 0, 0]],
                    "fx": 165,
                    "sx": 101,
                    "ix": 148,
                    "pal": 72
                }]
            }
        elif mode == "workMode":
            payload = {"on": True, "bri": 200, "ps": 3}
        elif mode == "shootingMode":
            payload = {"on": True, "bri": 200, "ps": 5}
        else:
            result["warnings"].append(f"Unknown strip mode '{strip_mode}'. Falling back to 'workMode'.")
            payload = {"on": True, "bri": 200, "ps": 1}

        resp = await self.send_wled_request(payload, self.WLED_IP)
        result["details"].append(resp)
        if resp.get("ok"):
            result["status"] = "success"
            result["message"] = f"Applied mode '{mode or 'workMode'}' to WLED."
        else:
            result["status"] = "error"
            result["message"] = f"Failed to apply mode '{mode or 'workMode'}'."
            if resp.get("error"):
                result["warnings"].append(resp.get("error"))

        return result


if __name__ == "__main__":
    # For quick local testing
    async def test():
        led = LEDStripController()
        res1 = await led.set_led_segment("all", [0, 255, 200], 200)
        print(res1)
        # res2 = await led.set_segment_mode("shootingMode")
        # print(res2)

    asyncio.run(test())