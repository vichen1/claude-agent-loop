"""SWE toolset — stub for now."""

TOOLS = [
    {
        "name": "run_tests",
        "description": "Run the test suite and return structured pass/fail results.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    if name == "run_tests":
        return "not implemented yet"
    return f"Unknown tool: {name}"
