import os
import uuid
from datetime import datetime
from typing import Annotated, Optional, TypedDict, Union
 
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
 
from tools import TOOL_KIT
 
load_dotenv()
 
 

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   
    context: Union[str, dict, None]           
 
 
class Agent:
    def __init__(self, instructions: str, model: str = "gpt-4o-mini"):
        self.instructions = instructions
 
        # ---- LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.0,
            base_url="...",
            api_key="openai key here",
        )
        self.llm_with_tools = self.llm.bind_tools(TOOL_KIT)
 
        self.graph = self._build_graph()
 
    # ---------------------------------------------------------------- nodes
    def _context_block(self, context) -> str:
        """Context awareness: current date/time + whatever the caller knows about the customer."""
        now = datetime.now()
        lines = ["", "## Current context",
                 f"- Current date/time: {now:%A, %Y-%m-%d %H:%M} (use this to resolve 'today', "
                 "'tomorrow', weekdays, 'this week'; pass dates to tools as YYYY-MM-DD)"]
        if isinstance(context, dict):
            lines += [f"- {k}: {v}" for k, v in context.items()]
        elif context:
            lines.append(f"- Customer info: {context}")
        return "\n".join(lines)
 
    def _agent_node(self, state: AgentState):
        system = SystemMessage(content=self.instructions + self._context_block(state.get("context")))
        try:
            reply = self.llm_with_tools.invoke([system] + state["messages"])
        except Exception as e:  # error handling: never crash the conversation
            reply = AIMessage(content=(
                "I'm sorry - I ran into a problem while preparing your recommendation "
                f"({type(e).__name__}). Please try again in a moment."))
        return {"messages": [reply]}
 
    # ---------------------------------------------------------------- graph
    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("agent", self._agent_node)
        # handle_tool_errors=True: a failing tool returns an error message to the LLM instead of raising
        g.add_node("tools", ToolNode(TOOL_KIT, handle_tool_errors=True))
        g.add_edge(START, "agent")
        g.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
        g.add_edge("tools", "agent")
        return g.compile()
 
    # ---------------------------------------------------------------- public API
    def invoke(self, question: str, context: Union[str, dict, None] = None) -> dict:
        """
        Ask the Energy Advisor a question about energy optimization.
 
        Args:
            question (str): The user's question
            context (str | dict): Optional customer context (location, devices, solar system...)
 
        Returns:
            dict: final graph state; response["messages"] holds the full trace
                  (the last message is the advisor's answer).
        """
        try:
            return self.graph.invoke(
                {"messages": [HumanMessage(content=question)], "context": context},
                config={"recursion_limit": 20},   # stops runaway tool loops
            )
        except Exception as e:
            return {"messages": [HumanMessage(content=question),
                                 AIMessage(content=f"Sorry, something went wrong: {e}")]}
 
    def get_agent_tools(self):
        """Get list of available tools for the Energy Advisor"""
        return [t.name for t in TOOL_KIT]