from pathlib import Path
import json, requests
from rapidfuzz import process
from typing import Literal
from app.backend.logger import log



contact_list_path = Path(__file__).resolve().parents[2] /"data"/ "contacts_10digit.json"

class CommunicationController:
    def __init__(self):
        with open(contact_list_path, "r") as f:
            self.contact_list = json.load(f)

        self.join_api_key = "eb3e0b7cc52d4acf95ecd77f5643f623"
        self.join_phone_id = "c6a07d0b1b9e470eb7181498d7eb8d49"
        self.join_tab_id = "8ee32ff238364678bf6ef90265a3c672"
        self.url = f"https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush"
    
    async def sim_call(self, contact_name: str):
        number, actual_name = await self.get_number(contact_name.lower()) # type: ignore
        params = {
                "apikey": self.join_api_key,
                "callnumber": number,
                "deviceId": self.join_phone_id
            }
        # print(f"calling {actual_name} : {number}")
        result = requests.get(self.url, params=params)
        return f"Call to {actual_name} initiated." if result.status_code == 200 else "Failed to initiate call."
    
    async def send_sim_message(self, contact_name: str, message_content: str):
        number, actual_name = await self.get_number(contact_name.lower()) # type: ignore
        number_with_country_code = f"91{number}"
        
        data = f"sim msg||{number_with_country_code}||{message_content}"
        params = {
            "apikey": self.join_api_key,
            "text": data,
            "deviceId": self.join_phone_id
        }
        result = requests.get(self.url, params=params)
        return f"Message sent to {actual_name} via sim phone." if result.status_code == 200 else "Failed to send message."
    
    
    async def whatsapp_call(self, contact_name: str, device: Literal["phone","tab"], call_type: str):
        number, actual_name = await self.get_number(contact_name.lower()) # type: ignore
        number_with_country_code = f"91{number}"
        if device == "phone":
            device_id = self.join_phone_id
        else:
            device_id = self.join_tab_id

        if call_type.lower() == "voice":
            data = f"whatsapp voice call||{number_with_country_code}"

        elif call_type.lower() == "video":
            data = f"whatsapp video call||{number_with_country_code}"

        params = {
            "apikey": self.join_api_key,
            "text": data,
            "deviceId": device_id
        }
        result = requests.get(self.url, params=params)
        return f"WhatsApp {call_type} call to {actual_name} via {device} initiated." if result.status_code == 200 else "Failed to initiate WhatsApp call."
    

    async def send_whatsapp_message(self, contact_name: str, device: Literal["phone","tab"], message_content: str) -> str:
        number, actual_name = await self.get_number(contact_name.lower()) # type: ignore
        number_with_country_code = f"91{number}"
        if device == "phone":
            device_id = self.join_phone_id
        else:
            device_id = self.join_tab_id

        data = f"whatsapp msg||{number_with_country_code}||{message_content}"
        
        params = {
            "apikey": self.join_api_key,
            "text": data,
            "deviceId": device_id
        }
        result = requests.get(self.url, params=params)
        return f"Message sent to {actual_name} via {device}." if result.status_code == 200 else "Failed to send message."



    async def get_number(self, name):
        choices = list(self.contact_list.keys())
        result = process.extractOne(name, choices, score_cutoff=50)
        if result:
            match, score, _ = result
            number = self.contact_list[match]
            return number, match
        else:
            return None # No match found
        
if __name__ == "__main__":
    comms = CommunicationController()
    import asyncio
    print(asyncio.run(comms.whatsapp_call("sister","phone","voice")))