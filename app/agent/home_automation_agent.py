from typing import Literal
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.backend.home_backend import HomeController, LEDStripController
from langgraph.prebuilt import create_react_agent
import os
from pathlib import Path
from langchain_core.tools import tool
from typing import List, Dict, Any 


# Load environment variables
from dotenv import load_dotenv
api_key_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=api_key_path, override=True)
api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model='gpt-4.1-mini', api_key=api_key) # type: ignore

home_controller = HomeController()
led_controller = LEDStripController()

@tool
async def appliance_control(controlled_appliance: str, controlled_state: Literal["on", "off"]) -> str:
    """
    Use this tool to turn any home appliance on or off. 
      
    controlled_appliance must be the EXACT name of the appliance.
    
    Available appliances: [
        "bedroom light", "bedroom fan", "bedroom bulb", "bathroom light", "stair light",
        "outdoor light", "outdoor camera", "pc", "home theater", "main led",
        "side led", "raspberry pi", "soldering iron"
      ]
    
    controlled_state must be 'on' or 'off'
    
    Alternative names of the appliances: side led also means back almary led, home theater also means speaker, outdoor camera also means cctv camera,
    stair light also means siri light. But make sure to use the name of the appliance from Avaliable appliances when using the tool.
    
    Example: appliance_control(controlled_appliance='bedroom fan', controlled_state='on')
    """
    return await home_controller.appliance_control(controlled_appliance, controlled_state)

@tool
async def set_led_segment(segment_name: str, rgb_colour_code: list[int], brightness_value: int = 200) -> Dict[str, Any]:
    """
    Use this tool to set the color and brightness of a specific LED strip segment or all segments.
    
    segment_name must be EXACTLY one of:
    [
      "front almary", "behind the money plant", "ceiling", "under laptop table",
      "under pc table", "ganesha almary", "shiva almary", "all", "back almary"
    ]
    
    rgb_colour_code must be a list of three integers in range 0–255, e.g. [255, 0, 0] for red.
    
    brightness_value must be an integer in range 0–255 (default=200).

    segment name all means all segments will be set to the same color and brightness.
    
    Example: set_led_segment(segment_name="ceiling", rgb_colour_code=[0, 255, 0], brightness_value=200)
    """
    return await led_controller.set_led_segment(segment_name, rgb_colour_code, brightness_value)


# @tool
# async def set_segment_mode(strip_mode: str) -> Dict[str, Any]:
#     """
#     Use this tool to apply a predefined mode/effect to the LED strip.
    
#     strip_mode must be one of:
#     - "musicSync"  → reactive lighting effect with music
#     - "workMode"   → steady bright lighting
#     - "shootingMode" → dim balanced lighting for video shooting
    
#     Example: set_segment_mode(strip_mode="musicSync")
#     """
#     return await led_controller.set_segment_mode(strip_mode)


home_agent_instruction = (
    "You are OM's Home Automation Agent.\n"
    "Your ONLY responsibility is to control smart home appliances and LED strip lights "
    "using the tools provided to you."
    
     "Strict Rules:\n"
    "- Always call the correct tool with the correct arguments.\n"
    "- Never answer general knowledge or unrelated questions.\n"
    "- If the request is outside your capabilities, politely decline.\n"
    "- Do not invent tools or devices not listed.\n"
    "- Keep responses minimal and only focused on device control.\n"
)

home_agent = create_react_agent(
    llm,
    tools=[appliance_control, set_led_segment],
    prompt=SystemMessage(content=home_agent_instruction)
)
