# dev-agent

A minimal agentic coding assistant built directly on the Claude Messages API
(no framework — you see the whole loop).

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Run

```bash
python agent.py "Read utils.py, find the bug, and fix it"
```

## How it works

1. You send a task as a user message, along with a list of tool schemas
   (`read_file`, `write_file`, `list_dir`, `run_bash`).
2. Claude replies. If it wants to act, the response has `stop_reason ==
   "tool_use"` and includes one or more `tool_use` blocks.
3. Your code executes those tools locally (`tools.py`) and sends the results
   back as a `tool_result` message.
4. Claude sees the results and decides what to do next — read more, edit,
   run tests, or stop and summarize.
5. This repeats until Claude stops requesting tools (`stop_reason !=
   "tool_use"`) or `MAX_TURNS` is hit.

That loop — call, check for tool_use, execute, feed back, repeat — is the
core of every agent, including Claude Code itself.

## Where to go next

- **Add tools**: web search, a code-diff/patch tool, git operations.
- **Parallel tool calls**: a single turn can contain multiple `tool_use`
  blocks — this scaffold already handles that (see the loop in `agent.py`).
- **Permissions**: right now `run_bash` and `write_file` execute
  unconditionally. For anything beyond a sandbox, add a confirmation step
  or an allowlist before executing.
- **Context management**: long sessions will grow `messages` indefinitely;
  look into prompt caching and context compaction once this gets used for
  real tasks.
- **Skip the boilerplate**: Anthropic's official Agent SDK
  (`pip install claude-agent-sdk`) gives you this same loop plus built-in
  file/bash/search tools, permission modes, and context management out of
  the box — worth trying once you understand what it's doing for you.
  https://docs.claude.com/en/docs/agent-sdk/overview
