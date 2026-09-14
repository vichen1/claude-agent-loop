#!/usr/bin/env python3
"""
Eval runner: run the agent against a suite of tasks and report results.

Each task folder contains:
    files/       starting state, copied to a temp dir per run
    prompt.txt   what the agent is told
    verify.sh    exit 0 = pass, non-zero = fail

Usage:
    python evals/runner.py                          # all swe tasks
    python evals/runner.py --suite ml
    python evals/runner.py --task 002-off-by-one    # one task
    python evals/runner.py --model claude-sonnet-5
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # project root
sys.path.insert(0, str(ROOT))

# Price per million tokens. Update if rates change.
PRICING = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
}


def cost(model, tok_in, tok_out):
    rates = PRICING.get(model)
    if not rates:
        return 0.0
    return tok_in / 1e6 * rates[0] + tok_out / 1e6 * rates[1]


def run_task(task_dir: Path, model: str, toolsets: list, max_turns: int):
    """Run one task in an isolated temp dir. Returns a result dict."""
    import agent as agent_mod
    from tools import load

    prompt = (task_dir / "prompt.txt").read_text().strip()
    result = {"task": task_dir.name, "passed": False, "error": None}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for f in (task_dir / "files").iterdir():
            shutil.copy2(f, tmp / f.name)

        cwd = Path.cwd()
        start = time.time()
        try:
            import os
            os.chdir(tmp)

            TOOLS, execute_tool = load(toolsets)
            agent_mod.MODEL = model
            agent_mod.MAX_TURNS = max_turns
            agent_mod.AUTO_APPROVE = True     # no interactive prompts in eval

            stats = agent_mod.run_agent(prompt, TOOLS, execute_tool, quiet=True)
            result.update(stats)

        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            os.chdir(cwd)
            result["seconds"] = round(time.time() - start, 1)
            return result

        os.chdir(cwd)
        result["seconds"] = round(time.time() - start, 1)

        # verify
        verify = task_dir / "verify.sh"
        try:
            v = subprocess.run(
                ["bash", str(verify)], cwd=tmp,
                capture_output=True, text=True, timeout=60,
            )
            result["passed"] = v.returncode == 0
            if v.returncode != 0 and v.stderr.strip():
                result["verify_stderr"] = v.stderr.strip()[:300]
        except subprocess.TimeoutExpired:
            result["error"] = "verify.sh timed out"

    return result


def main():
    ap = argparse.ArgumentParser(description="Run the agent against eval tasks.")
    ap.add_argument("--suite", default="swe", help="Task suite under evals/tasks/")
    ap.add_argument("--task", help="Run a single task by folder name")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--toolset", action="append", default=[])
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--out", default="evals/results.json")
    args = ap.parse_args()

    suite_dir = ROOT / "evals" / "tasks" / args.suite
    if not suite_dir.exists():
        sys.exit(f"No such suite: {suite_dir}")

    tasks = sorted(d for d in suite_dir.iterdir() if d.is_dir())
    if args.task:
        tasks = [t for t in tasks if t.name == args.task]
        if not tasks:
            sys.exit(f"No task named {args.task} in {args.suite}")

    print(f"Running {len(tasks)} task(s) | model={args.model} "
          f"| toolsets=core+{args.toolset or 'none'}\n")

    results = []
    for t in tasks:
        print(f"  {t.name:<28}", end="", flush=True)
        r = run_task(t, args.model, args.toolset, args.max_turns)
        results.append(r)
        mark = "PASS" if r["passed"] else "FAIL"
        extra = f"  ({r['error']})" if r.get("error") else ""
        print(f"{mark}  {r.get('turns','?'):>2} turns  "
              f"{r.get('seconds','?'):>5}s{extra}")

    # summary
    n = len(results)
    passed = sum(r["passed"] for r in results)
    tok_in = sum(r.get("input_tokens", 0) for r in results)
    tok_out = sum(r.get("output_tokens", 0) for r in results)
    turns = [r.get("turns", 0) for r in results if r.get("turns")]
    total_cost = cost(args.model, tok_in, tok_out)

    print(f"\n{'-'*56}")
    print(f"  passed        {passed}/{n}  ({passed/n*100:.0f}%)")
    if turns:
        print(f"  avg turns     {sum(turns)/len(turns):.1f}")
    print(f"  tokens        {tok_in:,} in / {tok_out:,} out")
    print(f"  cost          ${total_cost:.4f}  (${total_cost/n:.4f}/task)")
    print(f"{'-'*56}")

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "model": args.model,
        "toolsets": args.toolset,
        "suite": args.suite,
        "passed": passed,
        "total": n,
        "input_tokens": tok_in,
        "output_tokens": tok_out,
        "cost_usd": round(total_cost, 4),
        "results": results,
    }, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
