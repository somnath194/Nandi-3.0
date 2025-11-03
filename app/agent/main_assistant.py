from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from typing import TypedDict, Annotated
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain_core.tools import tool 
import os, asyncio

from app.agent.home_automation_agent import home_agent
from app.agent.os_controlling_agent import os_agent
from app.agent.communication_agent import communication_agent
from app.backend.logger import log



# ---------------------------
# Chat State
# ---------------------------
def smart_add_messages(existing: list, new: list | dict) -> list:
    """Custom reducer that allows replacement via special flag"""
    if isinstance(new, dict) and new.get("__replace__"):
        return new["messages"]
    
    return add_messages(existing, new) # type: ignore

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], smart_add_messages]
    summary: str | None

# ---------------------------
# Load API Key
# ---------------------------
api_key_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=api_key_path, override=True)
api_key = os.getenv("OPENAI_API_KEY")


# ---------------------------
# Tools
# ---------------------------
search = DuckDuckGoSearchRun()
calculator = PythonREPLTool()
# The first line was used by the chat_stream endpoint so don't change that line.
brain_agent_instruction = (
    "You are OM, the main helpful AI Assistant."
    "You handle general reasoning, search, calculations and user queries. "
    "If the user asks about controlling home devices, delegate the request "
    "to the Home Automation Agent by invoking the 'home_agent_delegate' tool."
    "If the user asks about controlling operating system based devices like open chrome on pc, delegate the request "
    "to the OS Agent by invoking the 'os_agent_delegate' tool."
    "If the user asks about communication tasks like calling or messaging, delegate the request "
    "to the Communication Agent by invoking the 'communication_agent_delegate' tool."
)


@tool
async def home_agent_delegate(user_query: str) -> str:
    """
    Delegate home automation requests to the Home Automation Agent.
    The Home agent capable of controlling smart home appliances and LED strip lights.
    Such as turn on bedroom light, turn off pc, set led color to red etc.
    """
    state = {"messages": [HumanMessage(content=user_query)]}
    result = await home_agent.ainvoke(state)

    for msg in result["messages"]:
        # if msg.type == "ai" and "tool_calls" in msg.additional_kwargs:
        #     log(f"[DEBUG] AI requested tools: {msg.additional_kwargs['tool_calls']}")
        if msg.type == "tool":
            log(f"Home Agent Tool Result: {msg.content}")

    return result["messages"][-1].content

@tool
async def os_agent_delegate(user_query: str) -> str:
    """
    Delegate Operation System based devices control requests to the OS Agent.
    The OS agent capable of handling pc, laptop, phone and tab controlling features and information.
    Such as application control requests like open da vinchi resolve on pc, close youtube on phone, search a dj song on youtube etc.
    """
    state = {"messages": [HumanMessage(content=user_query)]}
    result = await os_agent.ainvoke(state)
    
    for msg in result["messages"]:
        # if msg.type == "ai" and "tool_calls" in msg.additional_kwargs:
        #     log(f"[DEBUG] AI requested tools: {msg.additional_kwargs['tool_calls']}")
        if msg.type == "tool":
            log(f"Os Agent Tool Result: {msg.content}")

    return result["messages"][-1].content

@tool
async def communication_agent_delegate(user_query: str) -> str:
    """
    Delegate communication requests to the Communication Agent.
    The Communication agent capable of handling mobile phone communication tasks like calling or messaging.
    Such as make a whatsapp video call to mom, send a whatsapp message to sister etc.
    """
    state = {"messages": [HumanMessage(content=user_query)]}
    result = await communication_agent.ainvoke(state)
    
    for msg in result["messages"]:
        # if msg.type == "ai" and "tool_calls" in msg.additional_kwargs:
        #     log(f"[DEBUG] AI requested tools: {msg.additional_kwargs['tool_calls']}")
        if msg.type == "tool":
            log(f"Communication Agent Tool Result: {msg.content}")

    return result["messages"][-1].content

# ---------------------------
# Session Manager
# ---------------------------
class SessionManager:
    def __init__(self, checkpoint: MemorySaver):
        self.checkpoint = checkpoint

    def list_sessions(self):
        """Return all active session IDs."""
        return list(self.checkpoint.storage.keys())

    def clear_session(self, session_id: str):
        """Clear memory for a specific session."""
        if session_id in self.checkpoint.storage:
            del self.checkpoint.storage[session_id]
            return True
        return False

    def clear_all_sessions(self):
        """Clear all sessions."""
        self.checkpoint.storage.clear()


def extract_meaningful_context(messages):
    context_lines = []

    for msg in messages:
        # 🧍 Human messages
        if msg.type == "human":
            context_lines.append(f"User: {msg.content}")

        # 🤖 AI messages (may include tool calls or normal replies)
        elif msg.type == "ai":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for call in msg.tool_calls:
                    tool_name = call.get("name", "unknown_tool")
                    args = call.get("args", {})
                    # Keep only readable arguments
                    if isinstance(args, dict):
                        args_str = ", ".join(f"{k}: {v}" for k, v in args.items())
                    else:
                        args_str = str(args)
                    context_lines.append(f"Assistant invoked {tool_name}({args_str})")
            elif msg.content:
                context_lines.append(f"Assistant: {msg.content}")

        # 🧰 Tool result (response from a tool)
        elif msg.type == "tool":
            context_lines.append(f"Tool result: {msg.content}")
    # log(f"Cleaned context lines: {context_lines}")

    return "\n".join(context_lines)

def split_messages(messages: list[BaseMessage], trigger_turns: int = 12, keep_recent_turns: int = 6):
    """
    Splits messages intelligently by counting *human turns* (user messages).
    
    - If total human messages <= trigger_turns: returns ([], messages)
    - Otherwise: splits so the first `keep_recent_turns` human turns remain recent,
      and the rest are old (to be summarized).
    
    Ensures tool call blocks and AI follow-ups are not cut mid-sequence.
    """
    # Find indices of all human messages
    human_indices = [i for i, msg in enumerate(messages) if msg.type == "human"]
    log(f"Length of human turns: {len(human_indices)}")

    # Case 1: not enough turns → do nothing
    if len(human_indices) <= trigger_turns:
        return [], messages

    # Case 2: need summarization → find split boundary
    split_index = human_indices[-keep_recent_turns]  # index of the (N-th from end) human message

    # Move forward to safely finish any tool interaction (AI tool_calls, tool, AI follow-up)
    while split_index < len(messages):
        msg = messages[split_index]
        if msg.type == "tool" or (msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls): # type: ignore
            split_index += 1
            continue
        break

    old_messages = messages[:split_index]
    recent_messages = messages[split_index:]
    return old_messages, recent_messages



# ---------------------------
# Agent Manager
# ---------------------------
class MainAgentManager:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4.1-mini", api_key=api_key)  # type: ignore
        self.checkpoint = MemorySaver()
        self.session_manager = SessionManager(self.checkpoint)

        self.graph = StateGraph(ChatState)
        self.brain_agent = create_react_agent(
            self.llm,
            tools=[search, calculator, home_agent_delegate, os_agent_delegate, communication_agent_delegate],
            prompt=SystemMessage(content=brain_agent_instruction),
        )

        self.graph.add_node("chat_node", self.chat_node)
        self.graph.add_edge(START, "chat_node")
        self.graph.add_edge("chat_node", END)

        self.agent = self.graph.compile(checkpointer=self.checkpoint)


    async def _perform_background_summary(self, session_id: str):
        """
        Perform the actual summarization in background using the agent's update mechanism.
        This is called AFTER the response is sent to the user.
        """
        try:
            config = {"configurable": {"thread_id": session_id}}
            
            # Get current state from checkpoint
            state_snapshot = self.agent.get_state(config = config) # type: ignore
            current_state = state_snapshot.values
            
            messages = current_state.get("messages", [])
            summary_text = current_state.get("summary")

            # log(f"Length of messages: {len(messages)}")
            
            old_messages, recent_messages = split_messages(messages, trigger_turns=4, keep_recent_turns=2)

            # log(f"Length of old msgs:{len(old_messages)}")
            if not old_messages:
                return

            log(f"[BackgroundSummary] Summarizing {len(old_messages)} messages...")

            # Prepare messages for summarization
            # prepared_old_messages = prepare_messages_for_summarization(old_messages)
            
            summary_prompt = [
                    SystemMessage(content=(
                        "You are an assistant that maintains an ongoing summary of a long conversation. "
                        "Update and refine the summary using the new conversation messages provided. "
                        "Preserve important details, facts, context, user preferences, and tool usage results. "
                        "If a previous summary exists, merge it smoothly with the new details — do not discard any context."
                    ))
                ]

                # Include old summary as part of human message input
            combined_summary_input = (
                f"Previous summary:\n{summary_text or 'None'}\n\n"
                f"New messages to summarize:\n{extract_meaningful_context(old_messages)}"
            )

            summary_prompt.append(HumanMessage(content=combined_summary_input)) # type: ignore

            # Generate summary
            result = await self.llm.ainvoke(summary_prompt)
            new_summary_text = result.content.strip() # type: ignore

            # log(f"[BackgroundSummary] ✅ New summary: {new_summary_text}...")
            
            # Update state using the agent's update mechanism
            self.agent.update_state(
                    config, # type: ignore
                    {
                        "messages": {"__replace__": True, "messages": recent_messages},
                        "summary": new_summary_text,
                    }
            )
            
            log(f"[BackgroundSummary] ✅ State updated for session {session_id}")
            log(f"Updated Length of messages: {len(self.agent.get_state(config = config).values.get('messages', []))}") # type: ignore

        except Exception as e:
            log(f"[BackgroundSummary] ❌ Failed: {e}")
        
    
    async def chat_node(self, state: ChatState):
        """Single node execution."""
        messages = state["messages"]
        summary = state.get("summary")

        # 🔹 If a summary exists, prepend it as a system context message
        if summary:
            summary_message = SystemMessage(
                content=f"Conversation summary so far:\n{summary}\n\nUse this information as background context."
            )
            # We insert before all user/assistant messages to make it visible
            effective_messages = [summary_message] + messages
        else:
            effective_messages = messages

        initial_message_count = len(effective_messages)

        # 🔹 Pass both messages and summary context to the brain agent
        result = await self.brain_agent.ainvoke({"messages": effective_messages})
        new_messages = result["messages"][initial_message_count:]

        for msg in new_messages:
            # if msg.type == "ai" and "tool_calls" in msg.additional_kwargs:
            #     log(f"Main Agent AI requested tools: {msg.additional_kwargs['tool_calls']}")
            if msg.type == "tool":
                log(f"Main Agent Tool Result: {msg.content}")

        # Store messages only (no need to keep injected summary)
        return {"messages": result["messages"]}


    async def invoke(self, query: str, session_id: str = "default") -> str:
        """Public method for FastAPI/WebSocket."""
        initial_state = {"messages": [HumanMessage(content=query)]}
        config = {"configurable": {"thread_id": session_id}}
        result = await self.agent.ainvoke(initial_state, config=config) # type: ignore

        asyncio.create_task(self._perform_background_summary(session_id))

        return result["messages"][-1].content
    

    async def invoke_stream(self, query: str, session_id: str = "default"):
        """Stream partial responses as they are generated."""
        config = {"configurable": {"thread_id": session_id}}
        initial_state = {"messages": [HumanMessage(content=query)]}

        async for event in self.agent.astream_events(initial_state, config=config, version="v2"): # type: ignore
            # yield events directly to caller
            yield event

        # after stream ends, summarize in background
        asyncio.create_task(self._perform_background_summary(session_id))
