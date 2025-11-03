from typing import Literal
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.backend.os_backend import DeviceRouter
from langgraph.prebuilt import create_react_agent
import os
from pathlib import Path
from langchain_core.tools import tool 

# Load environment variables
from dotenv import load_dotenv
api_key_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=api_key_path, override=True)
api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model='gpt-4.1-mini', api_key=api_key) # type: ignore

device_router = DeviceRouter()

@tool
async def control_application(app_name: str, control_type: Literal["open", "close", "minimize", "maximize"], os_device: Literal["pc","laptop","phone","tab"]) -> str:
    """
    Use this tool to open close minimize or maximize any application as per user device.
    app_name is the application asked by user. 
    control_type must be 'open', 'close', 'minimize' or 'maximize'
    os_device must be 'pc', 'laptop', 'phone' or 'tab'
    Example: control_application(app_name='da vinchi resolve', control_type='open', os_device='pc')
    """
    return await device_router.execute(
        os_device,
        "AppControl",
        {"applicationName": app_name, "applicationControlType": control_type}
    )

@tool
async def open_website(url: str, os_device: Literal["pc","laptop","phone","tab"]) -> str:
    """
    Use this tool to open any website as per user device.
    url is the website asked by user.example open crickbuzz or youtube.
    you must provide full url with https or http from your knowledge. 
    os_device must be 'pc', 'laptop', 'phone' or 'tab'
    Example: open_website(url='https://www.youtube.com', os_device='phone')
    """
    return await device_router.execute(
        os_device,
        "WebsiteControl",
        {"websiteUrl": url}
    )

@tool
async def search_and_open(search_content: str, search_platform: Literal["google", "youtube"], os_device: Literal["pc","laptop","phone","tab"]) -> str:
    """
    Use this tool to search and open any website as per user device.
    search_content is the content asked by user to search on google or youtube. 
    search_platform must be 'google' or 'youtube'
    os_device must be 'pc', 'laptop', 'phone' or 'tab'
    Example: search_and_open(search_content='latest football news', search_platform='google', os_device='laptop')
    """
    return await device_router.execute(
        os_device,
        "SearchControl",
        {"searchPlatform": search_platform, "searchContent": search_content}
    )

@tool
async def simulate_type(typing_content: str, os_device: Literal["pc","laptop","phone","tab"]) -> str: 
    """
    Use this tool to simulate typing of any text on mentioned device.
    typing_content is the text asked by user to type on specific device. 
    Example: simulate_type(typing_content='hello world', os_device='laptop')
    """
    return await device_router.execute(
        os_device,
        "TypingControl",
        {"typingContent": typing_content}
    )

@tool
async def control_system_features(action: str, os_device: Literal["pc","laptop","phone","tab"]) -> str:
    """
    Use this tool to control system-level features on specific device.
    Available actions :[
    "minimize all window", "shutdown", "sleep", "restart", "switch window", 
    "pause", "hit enter", "full screen", "hit space", "select all", "copy", "paste"
                ]
    action must be one of the available actions and do not pass action which is not in avaliable actions. 
    Example: control_system_features(action="shutdown", os_device="pc")
    """
    return await device_router.execute(
        os_device,
        "SystemControl",
        {"action": action}
    )


@tool
async def device_information(info_type: Literal["ip address", "internet speed", "location"], os_device: Literal["pc","laptop","phone","tab"]) -> str:
    """
    Use this tool to get information from the device.
    info_type can be 'ip address', 'internet speed', 'location'.
    Example: device_information(info_type="location", os_device="phone")
    """
    return await device_router.execute(
        os_device,
        "DeviceInfo",
        {"informationType": info_type}
    )


@tool
async def adjust_settings(value_type: Literal["brightness", "volume"], adjustment_type: Literal["increase", "decrease", "set"], value: str, os_device: Literal["pc","laptop","phone","tab"]) -> str:
    """
    Use this tool to adjust system settings like brightness or volume.
    value_type must be 'brightness' or 'volume'.
    adjustment_type can be 'increase', 'decrease', or 'set'.
    value must be a percentage (e.g., '50%' or '20%').
    Example: adjust_settings(value_type="volume", adjustment_type="set", value="70%", os_device="pc")
    """
    return await device_router.execute(
        os_device,
        "AdjustSettings",
        {"valueType": value_type, "adjustmentType": adjustment_type, "value": value}
    )




os_agent_instruction = (
    "You are OM's OS Device Controlling Agent. "
    "Your ONLY job is to handle operating system devices control requests using the your avaliable tool."
    "the deices are pc, laptop, phone and tab with pc and laptop was windows os and phone and tab was android os"
    "If the user asks about anything else, politely decline."
    "Don't give unusefull information and do the job"
)

os_agent = create_react_agent(
    llm,
    tools=[control_application, open_website, search_and_open, simulate_type, control_system_features, device_information, adjust_settings],
    prompt=SystemMessage(content=os_agent_instruction)
)
