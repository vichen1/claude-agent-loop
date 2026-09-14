"""
Tool schemas (what Claude sees) + execution functions (what actually runs).
Keep these two things paired so it's obvious what each tool does when called.
"""
import subprocess
from pathlib import Path

# ---- Tool schemas sent to the API ----

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the full contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute file path"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write (overwrite) a file with the given content. Creates it if it doesn't exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        },
    },
    {
        "name": "run_bash",
        "description": "Run a shell command and return stdout/stderr. Use for running tests, git, etc.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]

# ---- Execution ----
DANGEROUS = {"run_bash", "write_file"}


def confirm(name: str, tool_input: dict) -> bool:
    if name not in DANGEROUS:
        return True
    print(f"\n  AGENT WANTS TO: {name}")
    print(f"  {tool_input}")
    return input("  Allow? [y/N] ").strip().lower() == "y"

def execute_tool(name: str, tool_input: dict) -> str:
    if not confirm(name, tool_input):
        return "User denied permission for this action."
    try:
        if name == "read_file":
            return Path(tool_input["path"]).read_text()

        if name == "write_file":
            p = Path(tool_input["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(tool_input["content"])
            return f"Wrote {len(tool_input['content'])} chars to {p}"

        if name == "list_dir":
            p = Path(tool_input.get("path", "."))
            return "\n".join(sorted(str(x) for x in p.iterdir()))

        if name == "run_bash":
            result = subprocess.run(
                tool_input["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return f"[exit {result.returncode}]\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

        return f"Unknown tool: {name}"

    except Exception as e:
        return f"Error running {name}: {e}"
