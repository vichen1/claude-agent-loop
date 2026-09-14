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
    {
        "name": "grep_codebase",
        "description": (
            "Search file contents for a regex pattern. Returns file:line:text. "
            "Use this FIRST to locate relevant code instead of reading files blindly. "
            "If two searches return no matches, stop guessing patterns — use "
            "list_dir or read_file to see what the code actually calls things."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex to search for"},
                "path": {"type": "string", "default": "."},
                "file_glob": {
                    "type": "string",
                    "description": "Optional filter, e.g. '*.py'",
                },
            },
            "required": ["pattern"],
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
        if name == "grep_codebase":
            import shutil
            pattern = tool_input["pattern"]
            path = tool_input.get("path", ".")
            glob = tool_input.get("file_glob")

            if shutil.which("rg"):
                cmd = ["rg", "--line-number", "--no-heading", "--color", "never",
                       "--max-count", "10", pattern, path]
                if glob:
                    cmd[1:1] = ["--glob", glob]
            else:
                cmd = ["grep", "-rn", "--exclude-dir=.venv", "--exclude-dir=.git",
                       "--exclude-dir=__pycache__", pattern, path]

            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            lines = [l for l in r.stdout.splitlines() if l.strip()]

            if not lines:
                return f"No matches for '{pattern}' in {path}."

            out = "\n".join(lines[:50])
            if len(lines) > 50:
                out += f"\n... {len(lines) - 50} more matches. Narrow your pattern."
            return out
        return f"Unknown tool: {name}"

    except Exception as e:
        return f"Error running {name}: {e}"
