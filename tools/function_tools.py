"""
KiroNav Function Calling Tools

These tools are used by Gemini Live API to interact with the user's screen.
The AI calls these tools to guide the user through software tasks.
"""

# Tool definitions for Gemini Live API
# These are passed as function_declarations in the LiveConnectConfig

KIRONAV_TOOLS = [
    {
        "name": "highlight_region",
        "description": "Highlight a specific region on the user's screen with a colored box and optional label. Use this to show the user exactly where to click or look.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "number",
                    "description": "X coordinate of the top-left corner (normalized 0-1, where 0 is left edge)"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate of the top-left corner (normalized 0-1, where 0 is top edge)"
                },
                "width": {
                    "type": "number",
                    "description": "Width of the highlight region (normalized 0-1)"
                },
                "height": {
                    "type": "number",
                    "description": "Height of the highlight region (normalized 0-1)"
                },
                "color": {
                    "type": "string",
                    "enum": ["red", "blue", "green", "yellow", "orange"],
                    "description": "Color of the highlight box"
                },
                "label": {
                    "type": "string",
                    "description": "Optional text label to show near the highlight"
                }
            },
            "required": ["x", "y", "width", "height", "color"]
        }
    },
    {
        "name": "draw_arrow",
        "description": "Draw an arrow from one point to another on the screen. Use this to show the direction or movement the user should make.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_x": {
                    "type": "number",
                    "description": "Starting X coordinate (normalized 0-1)"
                },
                "from_y": {
                    "type": "number",
                    "description": "Starting Y coordinate (normalized 0-1)"
                },
                "to_x": {
                    "type": "number",
                    "description": "Ending X coordinate (normalized 0-1)"
                },
                "to_y": {
                    "type": "number",
                    "description": "Ending Y coordinate (normalized 0-1)"
                },
                "color": {
                    "type": "string",
                    "enum": ["red", "blue", "green", "yellow", "orange"],
                    "description": "Color of the arrow"
                }
            },
            "required": ["from_x", "from_y", "to_x", "to_y", "color"]
        }
    },
    {
        "name": "show_step",
        "description": "Show a step instruction to the user in a speech bubble. Use this to tell the user what to do next.",
        "parameters": {
            "type": "object",
            "properties": {
                "step_number": {
                    "type": "integer",
                    "description": "Current step number (starting from 1)"
                },
                "instruction": {
                    "type": "string",
                    "description": "Clear, simple instruction for what the user should do"
                },
                "total_steps": {
                    "type": "integer",
                    "description": "Total number of steps in this tutorial"
                }
            },
            "required": ["step_number", "instruction", "total_steps"]
        }
    },
    {
        "name": "show_todolist",
        "description": "Show a markdown todolist for complex tasks with many steps. Use this when the task has more than 10 steps.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the tutorial/task"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of steps to complete the task"
                }
            },
            "required": ["title", "steps"]
        }
    },
    {
        "name": "complete_tutorial",
        "description": "Tutorial completed successfully. Use this when the user has finished all steps.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what the user accomplished"
                }
            },
            "required": ["summary"]
        }
    }
]


def get_tools_for_gemini():
    """
    Get tools formatted for Gemini Live API.
    
    Returns:
        list: Tools formatted for LiveConnectConfig
    """
    return [{"function_declarations": KIRONAV_TOOLS}]


def handle_tool_call(function_name: str, arguments: dict) -> dict:
    """
    Handle a tool call from Gemini Live API.
    
    This function is called when Gemini invokes one of our tools.
    It should be connected to the Flet UI to render overlays.
    
    Args:
        function_name: Name of the tool being called
        arguments: Arguments passed to the tool
        
    Returns:
        dict: Result to send back to Gemini
    """
    # This will be implemented in the UI layer
    # For now, return a placeholder
    return {"status": "ok", "tool": function_name, "args": arguments}
