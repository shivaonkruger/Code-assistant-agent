# main.py
# --------
# Entry point for the coding assistant. Runs a terminal loop that takes
# user input, passes it through the compiled LangGraph graph, and prints
# the agent's final response.
#
# CONCEPT: What graph.invoke() does
# ----------------------------------
# graph.invoke() takes an initial state dict and runs the graph to completion.
# "Completion" means the graph reached END — which in our case happens when
# the model produces a response with no tool calls.
#
# It blocks until the full loop finishes — all tool calls, all model
# invocations, everything — then returns the final state dict.
#
# The final state contains the complete message history:
#   [HumanMessage, AIMessage(tool_calls), ToolMessage, AIMessage(final)]
#
# We only care about the last message — the final AIMessage — to print
# to the terminal. But the full history is there if you want to inspect it.
#
# CONCEPT: Stateless vs Stateful invocation
# ------------------------------------------
# Notice that every call to graph.invoke() starts with ONLY the current
# user message — not the full conversation history. This means our agent
# is STATELESS across turns: it doesn't remember what you said last time.
#
# This is intentional for a learning project — it keeps each invocation
# isolated and easy to reason about. Each input → full agent loop → output.
#
# To make it stateful (remember previous turns), you'd maintain a messages
# list in main.py and append to it each turn, passing the growing history
# into graph.invoke() each time. LangGraph also has a built-in checkpointer
# system for persistence across sessions. Both are natural next steps.


import sys
from langchain_core.messages import HumanMessage
from agent import graph


# =============================================================================
# HELPERS
# =============================================================================

def print_separator():
    print("\n" + "─" * 60 + "\n")


def extract_final_response(state: dict) -> str:
    # The final state contains the full message history.
    # The last message is always the model's final answer —
    # an AIMessage with text content and no tool_calls.
    messages = state["messages"]
    last_message = messages[-1]
    return last_message.content


def print_agent_trace(state: dict):
    # CONCEPT: Inspecting the message history for learning
    # -----------------------------------------------------
    # This function prints every message in the final state so you can
    # see exactly what happened inside the agent loop.
    #
    # In production you'd remove this. For learning, it's invaluable —
    # you can see the tool_calls field on AIMessages, the ToolMessage
    # results, and how the message history grows with each step.
    #
    # Run the agent with --trace flag to enable this:
    #   python main.py --trace

    messages = state["messages"]
    print("\n[TRACE] Full message history:\n")

    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__

        if msg_type == "HumanMessage":
            print(f"  [{i}] HumanMessage:")
            print(f"      {msg.content[:100]}...")

        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"  [{i}] AIMessage (with tool calls):")
                for tc in msg.tool_calls:
                    print(f"      → tool: {tc['name']}")
                    for k, v in tc['args'].items():
                        preview = str(v)[:60].replace('\n', ' ')
                        print(f"        {k}: {preview}...")
            else:
                print(f"  [{i}] AIMessage (final response):")
                print(f"      {msg.content[:100]}...")

        elif msg_type == "ToolMessage":
            print(f"  [{i}] ToolMessage (result for tool call {msg.tool_call_id[:8]}...):")
            print(f"      {msg.content[:100]}...")

        print()


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    trace_mode = "--trace" in sys.argv

    print("╔══════════════════════════════════════════════════════════╗")
    print("║           Coding Assistant (LangGraph + Groq)            ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  Commands:                                                ║")
    print("║    quit / exit  →  exit the assistant                    ║")
    print("║    --trace flag →  run with: python main.py --trace      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("  I can explain code, debug it, or generate functions.")
    print("  What would you like help with?\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            # Handles Ctrl+C and Ctrl+D gracefully
            print("\n\nExiting. Goodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("\nExiting. Goodbye.")
            break

        print_separator()
        print("Agent is thinking...\n")

        try:
            # CONCEPT: Initial state for graph.invoke()
            # ------------------------------------------
            # We pass a dict that matches AgentState's shape.
            # {"messages": [HumanMessage(...)]} is the minimal valid state —
            # one message in the list, typed correctly.
            #
            # LangGraph validates this against AgentState at runtime.
            # If you passed a plain string instead of a HumanMessage,
            # it would still work (LangGraph coerces it), but being explicit
            # about message types is better practice.

            initial_state = {
                "messages": [HumanMessage(content=user_input)]
            }

            # Run the full agent loop. Blocks until END is reached.
            final_state = graph.invoke(initial_state)

            # Optionally print the full message trace for learning
            if trace_mode:
                print_agent_trace(final_state)
                print_separator()

            # Extract and print the final response
            response = extract_final_response(final_state)
            print(f"Assistant:\n\n{response}")

        except Exception as e:
            # Surface errors clearly rather than crashing silently.
            # Common causes: invalid API key, Groq rate limit, network issue.
            print(f"[Error] Something went wrong: {e}")
            print("Check your GROQ_API_KEY in .env and try again.")

        print_separator()


if __name__ == "__main__":
    main()