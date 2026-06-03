# ui.py
# ------
# Streamlit frontend for the coding assistant.
# Talks to FastAPI via HTTP — knows nothing about LangGraph directly.
#
# Layout:
#   Left (65%)  — chat interface
#   Right (35%) — live trace panel showing tool calls as they happen
#
# Run with: streamlit run ui.py
# (FastAPI must be running on port 8000 first)

import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

# =============================================================================
# PAGE CONFIG & STYLING
# =============================================================================

st.set_page_config(
    page_title="Coding Assistant",
    page_icon="⟨/⟩",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0d0d0d;
    color: #e8e8e8;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 1rem; max-width: 100%; }

/* ── Header ── */
.app-header {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 2rem;
    border-bottom: 1px solid #1f1f1f;
    padding-bottom: 1.2rem;
}
.app-title {
    font-size: 1.5rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
}
.app-subtitle {
    font-size: 0.78rem;
    color: #444;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── Chat messages ── */
.msg-wrap { margin-bottom: 1.4rem; }

.msg-user {
    background: #161616;
    border: 1px solid #252525;
    border-radius: 10px 10px 2px 10px;
    padding: 0.75rem 1rem;
    font-size: 0.92rem;
    line-height: 1.6;
    color: #cccccc;
    white-space: pre-wrap;
    word-break: break-word;
}
.msg-label-user {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #3a3a3a;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}

.msg-assistant {
    background: #111;
    border: 1px solid #1e1e1e;
    border-left: 3px solid #c0392b;
    border-radius: 2px 10px 10px 10px;
    padding: 0.85rem 1rem;
    font-size: 0.92rem;
    line-height: 1.7;
    color: #e0e0e0;
    white-space: pre-wrap;
    word-break: break-word;
}
.msg-label-assistant {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #c0392b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}

/* ── Trace panel ── */
.trace-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #333;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1a1a1a;
}

.trace-empty {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #2a2a2a;
    text-align: center;
    padding: 2rem 0;
}

.trace-event {
    border-radius: 6px;
    padding: 0.65rem 0.85rem;
    margin-bottom: 0.6rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    line-height: 1.5;
}
.trace-tool-call {
    background: #0e1a10;
    border: 1px solid #1a3520;
    color: #4caf7d;
}
.trace-tool-result {
    background: #0f0f1a;
    border: 1px solid #1e1e35;
    color: #7b8fcf;
}
.trace-final {
    background: #1a0e0e;
    border: 1px solid #351a1a;
    color: #c0392b;
}
.trace-error {
    background: #1a0a0a;
    border: 1px solid #4a1010;
    color: #e74c3c;
}

.trace-event-label {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    opacity: 0.6;
    margin-bottom: 3px;
}
.trace-event-body {
    word-break: break-word;
    white-space: pre-wrap;
}

/* ── Tool badge ── */
.tool-badge {
    display: inline-block;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 1px 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #888;
    margin-left: 6px;
}

/* ── Input area ── */
.stTextArea textarea {
    background: #111 !important;
    border: 1px solid #252525 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    resize: vertical !important;
}
.stTextArea textarea:focus {
    border-color: #c0392b !important;
    box-shadow: 0 0 0 2px rgba(192, 57, 43, 0.15) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #c0392b !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 1.2rem !important;
    letter-spacing: 0.03em !important;
    transition: background 0.15s ease !important;
}
.stButton > button:hover {
    background: #a93226 !important;
}

/* ── Divider ── */
.col-divider {
    border-left: 1px solid #1a1a1a;
    min-height: 60vh;
    padding-left: 1.5rem;
}

/* ── Thinking indicator ── */
.thinking {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #3a3a3a;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}

/* ── Scrollable chat area ── */
.chat-scroll {
    max-height: 62vh;
    overflow-y: auto;
    padding-right: 4px;
    scrollbar-width: thin;
    scrollbar-color: #222 transparent;
}
.trace-scroll {
    max-height: 62vh;
    overflow-y: auto;
    padding-right: 4px;
    scrollbar-width: thin;
    scrollbar-color: #222 transparent;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

# Streamlit reruns the entire script on every interaction.
# st.session_state persists data across reruns within the same session.

if "messages" not in st.session_state:
    st.session_state.messages = []       # list of {role, content}

if "trace_events" not in st.session_state:
    st.session_state.trace_events = []   # list of {type, ...} per conversation turn

if "current_turn_trace" not in st.session_state:
    st.session_state.current_turn_trace = []


# =============================================================================
# HELPERS
# =============================================================================

def render_trace_event(event: dict):
    """Render a single trace event as styled HTML."""
    t = event.get("type")

    if t == "tool_calls":
        for call in event.get("calls", []):
            tool_name = call["tool"]
            args = call.get("args", {})
            args_preview = ", ".join(
                f"{k}={repr(str(v)[:40])}" for k, v in args.items()
            )
            st.markdown(f"""
            <div class="trace-event trace-tool-call">
                <div class="trace-event-label">→ tool call</div>
                <div class="trace-event-body"><strong>{tool_name}</strong>({args_preview})</div>
            </div>
            """, unsafe_allow_html=True)

    elif t == "tool_results":
        for result in event.get("results", []):
            tool_name = result.get("tool", "unknown")
            content = result.get("content", "")[:200]
            st.markdown(f"""
            <div class="trace-event trace-tool-result">
                <div class="trace-event-label">← tool result · {tool_name}</div>
                <div class="trace-event-body">{content}...</div>
            </div>
            """, unsafe_allow_html=True)

    elif t == "final":
        st.markdown(f"""
        <div class="trace-event trace-final">
            <div class="trace-event-label">✓ final answer</div>
            <div class="trace-event-body">Response generated</div>
        </div>
        """, unsafe_allow_html=True)

    elif t == "error":
        st.markdown(f"""
        <div class="trace-event trace-error">
            <div class="trace-event-label">✗ error</div>
            <div class="trace-event-body">{event.get('content', '')}</div>
        </div>
        """, unsafe_allow_html=True)


def call_api_stream(message: str):
    """
    Call POST /chat and yield parsed event dicts as they stream in.

    CONCEPT: Consuming a streaming HTTP response in Python
    -------------------------------------------------------
    requests.post() with stream=True doesn't download the full response.
    It keeps the connection open and lets you read line by line.
    iter_lines() yields each newline-delimited chunk as it arrives.
    We parse each line as JSON — matching what api.py yields.
    """
    try:
        with requests.post(
            f"{API_URL}/chat",
            json={"message": message},
            stream=True,
            timeout=60
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        event = json.loads(line.decode("utf-8"))
                        yield event
                    except json.JSONDecodeError:
                        continue
    except requests.exceptions.ConnectionError:
        yield {
            "type": "error",
            "content": "Cannot connect to API server. Run: uvicorn api:app --reload --port 8000"
        }
    except Exception as e:
        yield {"type": "error", "content": str(e)}


# =============================================================================
# LAYOUT
# =============================================================================

st.markdown("""
<div class="app-header">
    <span class="app-title">⟨/⟩ Coding Assistant</span>
    <span class="app-subtitle">LangGraph · Groq · llama-3.3-70b</span>
</div>
""", unsafe_allow_html=True)

col_chat, col_trace = st.columns([65, 35])

# =============================================================================
# LEFT COLUMN — Chat
# =============================================================================

with col_chat:
    # Render chat history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center; padding: 3rem 0; color: #2a2a2a;
                        font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">
                explain · debug · generate
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="msg-wrap">
                        <div class="msg-label-user">You</div>
                        <div class="msg-user">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="msg-wrap">
                        <div class="msg-label-assistant">Assistant</div>
                        <div class="msg-assistant">{msg["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    # Input area
    user_input = st.text_area(
        label="",
        placeholder="Paste code or describe what you need...\n(Shift+Enter for new line)",
        height=120,
        key="input_box",
        label_visibility="collapsed"
    )

    btn_col, clear_col = st.columns([5, 1])
    with btn_col:
        send = st.button("Send", use_container_width=True)
    with clear_col:
        if st.button("↺", use_container_width=True, help="Clear chat"):
            st.session_state.messages = []
            st.session_state.trace_events = []
            st.session_state.current_turn_trace = []
            st.rerun()


# =============================================================================
# RIGHT COLUMN — Trace Panel
# =============================================================================

with col_trace:
    st.markdown('<div class="col-divider">', unsafe_allow_html=True)
    st.markdown('<div class="trace-header">Agent Trace</div>', unsafe_allow_html=True)

    trace_container = st.container()
    with trace_container:
        if not st.session_state.trace_events:
            st.markdown(
                '<div class="trace-empty">tool calls will appear here</div>',
                unsafe_allow_html=True
            )
        else:
            for event in st.session_state.trace_events:
                render_trace_event(event)

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# SEND HANDLER
# =============================================================================

if send and user_input.strip():
    user_message = user_input.strip()

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_message})
    st.session_state.current_turn_trace = []

    # Stream the response
    # We collect the final answer from the stream, and render trace events live
    final_answer = ""
    error_occurred = False

    # Streamlit placeholder lets us update a single UI slot across reruns
    # We use it to show a "thinking..." indicator while streaming
    with col_chat:
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown(
            '<div class="thinking">● agent is thinking...</div>',
            unsafe_allow_html=True
        )

    with col_trace:
        live_trace = st.empty()

    for event in call_api_stream(user_message):
        event_type = event.get("type")

        if event_type == "final":
            final_answer = event.get("content", "")
            st.session_state.current_turn_trace.append(event)

        elif event_type == "error":
            final_answer = f"Error: {event.get('content', 'Unknown error')}"
            st.session_state.current_turn_trace.append(event)
            error_occurred = True

        else:
            # tool_calls or tool_results — add to trace and re-render
            st.session_state.current_turn_trace.append(event)

        # Merge current turn trace into full trace history for display
        st.session_state.trace_events = st.session_state.current_turn_trace

    # Add assistant response to chat history
    st.session_state.messages.append({
        "role": "assistant",
        "content": final_answer or "No response received."
    })

    # Rerun to refresh the full UI with updated state
    st.rerun()