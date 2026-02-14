import paho.mqtt.client as paho
import asyncio
import time
# from app.core.logs import logs_push
from typing import List, Dict, Any
from app.backend.logger import log

from app.backend.home_backend import HomeController

home_controller = HomeController()



class ModeSelector:
    def __init__(self):
        pass
        

    async def set_mode(self, mode: str) -> str:

        if mode == 'work':

            await home_controller.appliance_control("pc", "on")
            await home_controller.appliance_control("main led", "on")
            await home_controller.appliance_control("side led", "on") 
            log("🔧 Setting mode to WORK.")
            
        return f"Mode set to '{mode}'. (Note: Mode switching functionality is currently under development.)"