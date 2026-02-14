from typing import Literal
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.backend.mode_selector_backend import ModeSelector
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

mode_selector = ModeSelector()


@tool
async def mode_executor(mode: Literal['work','sleep','party']) -> str:
    """
    Use this tool to set the mode of the smart home. 
    The mode will determine the behavior of other agents and devices in the home.
    
    mode must be 'work', 'sleep', or 'party'.
    
    Example: mode_selector(mode='sleep')
    """
    return await mode_selector.set_mode(mode)


mode_agent_instruction = (
    "You are OM's Mode Selector Agent.\n"
    "Your ONLY responsibility is to set the current mode of the smart home using the provided tool.\n"
    "The mode you set will influence the behavior of other agents and devices in the home.\n"
    "like work mode or party mode"

    
     "Strict Rules:\n"
    "- Always call the correct tool with the correct arguments.\n"
    "- Never answer general knowledge or unrelated questions.\n"
    "- If the request is outside your capabilities, politely decline.\n"
    "- Do not invent tools which not listed.\n"
    "- Keep responses minimal and only focused on device control.\n"
)

mode_selector_agent = create_react_agent(
    llm,
    tools=[mode_executor],
    prompt=SystemMessage(content=mode_agent_instruction)
)

