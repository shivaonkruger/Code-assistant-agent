import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from state import AgentState
from tools import tools
from prompts import SYSTEM_PROMPT

load_dotenv()


llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,     
)


llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> dict:
    messages = state["messages"]


    messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + messages


    response = llm_with_tools.invoke(messages_with_system)

    return {"messages": [response]}


tool_node = ToolNode(tools)




def should_use_tool(state: AgentState) -> str:


    last_message = state["messages"][-1]


    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node" 
    return END


def build_graph():


    graph = StateGraph(AgentState)

    graph.add_node("agent_node", agent_node)
    graph.add_node("tool_node", tool_node)

    graph.set_entry_point("agent_node")


    graph.add_conditional_edges(
        "agent_node",
        should_use_tool,
        {
            "tool_node": "tool_node",
            END: END,
        }
    )

    graph.add_edge("tool_node", "agent_node")


    return graph.compile()

graph = build_graph()