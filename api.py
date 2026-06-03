# api.py
# -------
# FastAPI server that wraps the LangGraph agent and exposes it over HTTP.
#
# CONCEPT: Why FastAPI in front of LangGraph?
# --------------------------------------------
# LangGraph runs in Python. Streamlit runs in Python. You could call the
# graph directly from Streamlit — but then your UI and your agent logic
# are coupled. If you later want a mobile app, a CLI, or a different
# frontend, you'd have to rewrite the integration each time.
#
# FastAPI gives you a clean HTTP boundary:
#   Streamlit → POST /chat → FastAPI → graph.invoke() → response
#
# Streamlit becomes just a consumer of an API. The agent is independently
# runnable and testable with curl or any HTTP client.
#
# CONCEPT: Streaming with Server-Sent Events (SSE)
# -------------------------------------------------
# graph.invoke() blocks until the full loop completes. For a chat UI that
# feels responsive, we want to stream tokens as they arrive rather than
# wait for the full response.
#
# We use StreamingResponse with graph.stream() for this. LangGraph's
# stream() yields state snapshots after each node completes — so the
# frontend gets updates as tool calls happen, not just at the end.
# This is what powers the "trace panel showing tool calls as they happen."


import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import json

from agent import graph

load_dotenv()

app = FastAPI(title="Coding Assistant API")

# Allow Streamlit (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str

# We don't define a response model because /chat uses StreamingResponse —
# the response is a stream of JSON lines, not a single JSON object.


# =============================================================================
# STREAMING HELPER
# =============================================================================

def extract_trace_event(chunk: dict) -> dict | None:
    # CONCEPT: LangGraph stream() output
    # ------------------------------------
    # graph.stream() yields dicts like:
    #   {"agent_node": {"messages": [AIMessage(...)]}}
    #   {"tool_node":  {"messages": [ToolMessage(...)]}}
    #
    # The key is the node name. The value is the state update that node
    # returned. We inspect each chunk to figure out what happened and
    # build a structured event for the frontend.
    #
    # We yield three event types:
    #   {"type": "tool_call",   "tool": "explain_code", "args": {...}}
    #   {"type": "tool_result", "tool": "explain_code", "content": "..."}
    #   {"type": "final",       "content": "..."}

    if "agent_node" in chunk:
        messages = chunk["agent_node"]["messages"]
        last = messages[-1]

        # AIMessage with tool_calls → model decided to use a tool
        if isinstance(last, AIMessage) and last.tool_calls:
            events = []
            for tc in last.tool_calls:
                events.append({
                    "type": "tool_call",
                    "tool": tc["name"],
                    "args": tc["args"],
                    "call_id": tc["id"]
                })
            return {"type": "tool_calls", "calls": events}

        # AIMessage without tool_calls → final answer
        if isinstance(last, AIMessage) and not last.tool_calls:
            return {
                "type": "final",
                "content": last.content
            }

    if "tool_node" in chunk:
        messages = chunk["tool_node"]["messages"]
        events = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                # ToolMessage.name holds which tool produced this result
                events.append({
                    "type": "tool_result",
                    "tool": getattr(msg, "name", "unknown"),
                    "call_id": msg.tool_call_id,
                    "content": msg.content[:300]  # truncate for UI display
                })
        return {"type": "tool_results", "results": events}

    return None


async def stream_agent(message: str):
    # CONCEPT: graph.stream() vs graph.invoke()
    # ------------------------------------------
    # graph.invoke()  → runs to completion, returns final state
    # graph.stream()  → yields state updates after each node, then ends
    #
    # stream() takes the same initial state dict as invoke().
    # It yields one chunk per node execution, in order.
    # We iterate over these chunks, convert each to a JSON event,
    # and yield it as a line in the SSE stream.
    #
    # The frontend reads these lines as they arrive and updates the UI
    # incrementally — tool calls appear in the trace panel the moment
    # the agent node finishes, before the tool even runs.

    initial_state = {"messages": [HumanMessage(content=message)]}

    try:
        for chunk in graph.stream(initial_state):
            event = extract_trace_event(chunk)
            if event:
                # Yield each event as a JSON line (newline-delimited JSON)
                # Streamlit reads these line by line using iter_lines()
                yield json.dumps(event) + "\n"
    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
def health():
    # Simple health check — useful to confirm the server is running
    # before you start the Streamlit UI.
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    # CONCEPT: StreamingResponse
    # ---------------------------
    # Instead of computing the full response and returning it at once,
    # StreamingResponse takes an async generator and sends its yielded
    # values to the client as they're produced.
    #
    # media_type="text/plain" means we're sending newline-delimited JSON.
    # Each line is a complete JSON object — an event from the agent loop.
    # The Streamlit frontend reads these lines and updates the UI per event.

    return StreamingResponse(
        stream_agent(request.message),
        media_type="text/plain"
    )


# =============================================================================
# RUN
# =============================================================================

# Run with: uvicorn api:app --reload --port 8000
#
# --reload  → restarts the server on file changes (good for development)
# --port    → Streamlit uses 8501 by default, so we use 8000 for FastAPI

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)