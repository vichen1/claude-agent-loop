"""
A minimal agentic coding assistant built directly on the Messages API.

The core idea: send messages -> if Claude wants to use a tool, run it locally,
append the result, and call again. Repeat until Claude stops asking for tools.
This loop IS what frameworks like the Agent SDK / Claude Code do under the hood.
"""
from dotenv import load_dotenv
load_dotenv()  # reads ANTHROPIC_API_KEY from .env

from anthropic import Anthropic
from tools import load

# Start on Haiku while learning the loop — half the input cost of Sonnet.
# Switch to "claude-sonnet-5" once the plumbing works.
MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 6  # safety cap so a buggy loop can't run forever

SYSTEM_PROMPT = """You are a careful coding assistant with access to a local
filesystem and shell via tools. Before making changes:
- Read relevant files first to understand context.
- Make minimal, targeted edits.
- After writing code, run it (tests, linter, or the script itself) to verify it works.
- Explain what you did briefly at the end.
"""

client = Anthropic()  # picks up ANTHROPIC_API_KEY automatically


def run_agent(task: str, TOOLS, execute_tool):
    messages = [{"role": "user", "content": task}]

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Watch these numbers climb — input grows every turn because the whole
        # history is resent. That's why prompt caching and compaction exist.
        print(
            f"\n[tokens] in={response.usage.input_tokens} "
            f"out={response.usage.output_tokens}"
        )

        for block in response.content:
            if block.type == "text":
                print(f"[Claude] {block.text}")

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break  # Claude is done — no more tools requested

        # Execute every tool call in this turn, collect results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[tool] {block.name}({block.input})")
                result = execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    else:
        print(f"\n[stopped: hit MAX_TURNS={MAX_TURNS}]")

    return messages


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Minimal coding agent.")
    parser.add_argument("task", help="What you want the agent to do.")
    parser.add_argument(
        "--toolset", action="append", default=[],
        help="Optional toolset to load (repeatable): swe, ml. core is always on.",
    )
    args = parser.parse_args()

    try:
        TOOLS, execute_tool = load(args.toolset)
    except ValueError as e:
        parser.error(str(e))
    print(f"[toolsets] core + {args.toolset or 'none'} -> {len(TOOLS)} tools")

    run_agent(args.task, TOOLS, execute_tool)
