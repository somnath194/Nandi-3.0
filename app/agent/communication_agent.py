from typing import Literal
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.backend.communication_backend import CommunicationController
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

communication_controller = CommunicationController()


@tool
async def sim_call(contact_name: str) -> str:
    """
    Use this tool to do a phone call to a contact from mobile phone.
    
    contact_name must be the EXACT name of the contact.
    
    Example: sim_call(contact_name='sister')
    """
    return await communication_controller.sim_call(contact_name)

@tool
async def send_sim_message(contact_name: str, message_content: str) -> str:
    """
    Use this tool to send a message to a contact from mobile phone.

    contact_name must be the EXACT name of the contact.
    
    message_content is the text message to be sent.
    
    Example: send_sim_message(contact_name='ma', message_content='Please call me back.')
    """
    return await communication_controller.send_sim_message(contact_name, message_content)

@tool
async def whatsapp_call(contact_name: str, device: Literal['phone','tab'], call_type: Literal["voice", "video"]) -> str:
    """
    Use this tool to do a WhatsApp voice or video call to a contact from mobile phone.
    
    contact_name must be the EXACT name of the contact.
    
    call_type must be 'voice' or 'video'
    
    Example: whatsapp_call(contact_name='mom',device = 'phone', call_type='video')
    """
    return await communication_controller.whatsapp_call(contact_name, device, call_type)

@tool
async def send_whatsapp_message(contact_name: str,device: Literal['phone','tab'], message_content: str) -> str:
    """
    Use this tool to send a message to a contact from mobile phone.

    message_media must be sim or whatsapp.
    
    contact_name must be the EXACT name of the contact.
    
    message_content is the text message to be sent.
    
    Example: send_whatsapp_message(contact_name='sundaram', device = 'phone', message_content='Hello, how are you?')
    """
    return await communication_controller.send_whatsapp_message(contact_name, device, message_content)


communication_agent_instruction = (
    "You are OM's Communication Automation Agent.\n"
    "Your ONLY responsibility is to manage communication tasks on my mobile phone like calling or messeging.\n"
    "using the tools provided to you."
    
     "Strict Rules:\n"
    "- Always call the correct tool with the correct arguments.\n"
    "- Never answer general knowledge or unrelated questions.\n"
    "- If the request is outside your capabilities, politely decline.\n"
    "- Do not invent tools which not listed.\n"
    "- Keep responses minimal and only focused on device control.\n"
)

communication_agent = create_react_agent(
    llm,
    tools=[sim_call,send_sim_message, whatsapp_call, send_whatsapp_message],
    prompt=SystemMessage(content=communication_agent_instruction)
)
