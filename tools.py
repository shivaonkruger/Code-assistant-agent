

from langchain_core.tools import tool



@tool
def explain_code(code: str) -> str:
    """
    Explains what a given piece of code does in plain English.
    Use this when the user wants to understand code — what it does,
    how it works, what each part means. Do not use this for fixing bugs.

    Args:
        code: The code snippet to explain.
    """

    return f"[explain_code tool] Received code to explain:\n\n{code}\n\nAnalyze this code and provide a clear, structured explanation of what it does, how it works, and what each significant part means."



@tool
def debug_code(code: str, error: str = "") -> str:
    """
    Debugs a piece of code by identifying bugs and suggesting fixes.
    Use this when the user reports an error, unexpected behavior, or asks
    to fix code. Optionally accepts an error message to provide more context.
    Do not use this just to explain what code does.

    Args:
        code: The buggy code to debug.
        error: The error message or description of unexpected behavior (optional).
    """

    if error:
        return (
            f"[debug_code tool] Received code with error:\n\n"
            f"Code:\n{code}\n\n"
            f"Error:\n{error}\n\n"
            f"Identify the bug(s), explain why they occur, and provide the corrected code."
        )
    else:
        return (
            f"[debug_code tool] Received code to debug (no error message provided):\n\n"
            f"Code:\n{code}\n\n"
            f"Identify any bugs or issues, explain what's wrong, and provide the corrected code."
        )


@tool
def generate_function(description: str, language: str = "Python") -> str:
    """
    Generates a complete function based on a plain English description.
    Use this when the user asks to write, create, or generate a function
    or piece of code from scratch. Do not use this for explaining or debugging
    existing code.

    Args:
        description: Plain English description of what the function should do.
        language: The programming language to generate the function in. Defaults to Python.
    """
    return (
        f"[generate_function tool] Received function generation request:\n\n"
        f"Description: {description}\n"
        f"Language: {language}\n\n"
        f"Generate a complete, working {language} function that fulfills this description. "
        f"Include the function signature, implementation, and a brief docstring."
    )


tools = [explain_code, debug_code, generate_function]