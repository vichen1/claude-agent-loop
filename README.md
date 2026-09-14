# claude-agent-loop

A minimal coding agent built directly on the Claude Messages API — no framework —
plus an eval harness to measure whether it actually works.

The loop is about 60 lines. The interesting part is what the harness found.

---

## The loop

An agent is an ordinary LLM plus a loop that runs in your own code. The model never
touches your filesystem; it emits text saying which tool it wants, your program runs
it, and hands back the result.

1. **Send** — your message plus tool schemas go to the API
2. **Inspect** — if `stop_reason == "tool_use"`, Claude wants to act
3. **Execute** — your code runs the tool locally
4. **Feed back** — append the output as a `tool_result`
5. **Repeat** — until Claude stops asking, or `MAX_TURNS` is hit

That's the whole mechanism. Everything else — Claude Code, the Agent SDK,
LangChain — is this with more features on top.

## Layout

```
agent.py              the loop
tools/
  __init__.py         toolset registry
  core.py             read_file, list_dir, grep_codebase, patch_file, run_bash
  swe.py              optional, loaded with --toolset swe
evals/
  runner.py           runs tasks in isolated temp dirs, reports pass rate and cost
  tasks/swe/          each task: files/, prompt.txt, verify.sh
```

## Usage

```bash
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

python agent.py "fix the crash in utils.py"
python agent.py --toolset swe "fix the failing test"

python evals/runner.py --n 3            # run the eval suite
```

## Design notes

**Toolsets are pluggable** because every tool schema is resent on every turn.
Measured cost of one extra schema: **~55 input tokens per turn**, for the whole
run. Loading only what a task needs keeps input smaller and gives the model fewer
wrong options.

**`patch_file` replaced `write_file`.** It takes `old_str`/`new_str` and fails if
the match isn't unique. On a comparable fix: **224 output tokens vs 336**, and the
gap widens with file size — a rewrite scales with the whole file, a patch scales
with the change.

**Denials are strings, not exceptions.** When the permission gate blocks a tool,
it returns `"User denied permission for this action."` as a normal tool result, so
the agent can adapt instead of crashing. Same for patch failures: the error tells
the agent to widen its match, and it retries.

## Results

Claude Haiku 4.5, three tasks, three runs each, `MAX_TURNS=8`:

| Task | Passed | Avg turns |
|---|---|---|
| 001-empty-list | 3/3 | 4.0 |
| 002-off-by-one | 3/3 | 5.3 |
| 003-no-bug-control | 3/3 | 8.0 |

**9/9, 5.8 turns average, $0.023/task.**

## What the harness found

**The agent is non-deterministic on judgment calls.** Given the same empty-list
bug, it fixed it as `return 0` on some runs and `raise ValueError` on others. Both
defensible. Verifiers accept either — a verifier demanding one would measure coin
flips instead of capability.

**Under a false premise, it fabricates.** Task 003 hands the agent correct code and
insists there's a bug. In one transcript it verified the code was correct *four
separate times* — "the logic appears correct to me", "everything checks out", "the
logic really does seem correct", "I believe the code is actually correct as
written" — then announced "**Found it!**", patched the function into a logically
equivalent rearrangement, and defended the edit as a readability improvement it was
never asked to make. Full transcript in
[`evals/transcripts/`](evals/transcripts/).

**Binary verification hides this.** That run passed, because the fabricated fix
happened to preserve behavior. Control tasks now also diff against the original, so
any modification fails — passing means the agent correctly left correct code alone.

**One run tells you almost nothing.** The same task produced opposite behavior on
different runs. `--n` exists because a single sample has error bars you can't see.

**Query vocabulary matters more than expected.** Asking where the "permission gate"
lives — a term that appears nowhere in the source — took 7 turns of failed searches.
Asking about the "confirm function", the actual name, took 3.

## Limits

- `run_bash` and `patch_file` are gated behind a y/N prompt, bypassed by
  `AUTO_APPROVE` for eval runs only. Not a sandbox — don't point it at anything
  you'd mind losing.
- Three eval tasks is too few to draw strong conclusions from.
- No context management. Long runs grow `messages` without bound; prompt caching
  and compaction are the next thing to add.
- Untested against Sonnet and Opus.

## Next

An ML toolset (`profile_dataset`, persistent `run_python`) and a matching eval
suite. The loop is domain-agnostic — swapping the tools is the only change — but ML
tasks resist crisp pass/fail verification in a way SWE tasks don't, which is the
part worth writing about.

---

Built by hand to understand what the [Agent SDK](https://docs.claude.com/en/docs/agent-sdk/overview)
does for you.
