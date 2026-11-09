"""Readable tick-by-tick transcript of one session: each agent's reasoning, tool calls and board pushes.

    python3 swarm2/trace.py runs2_ec2/mx-wrong/mx-wrong-d0-planted.json > traces/mx-wrong-d0-planted.md
"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from analyze_mx import outcome  # noqa: E402

CUT = 600  # tool output chars shown


def fence(s: str) -> str:
    return "```\n" + s.replace("```", "'''") + "\n```"


def main(path: str) -> None:
    s = json.loads(open(path).read())
    arm = "PLANTED (hook post on the board)" if s["planted"] else "CONTROL (placebo post)"
    print(f"# {s['sid']}: {arm}\n\nstatus: {s['status']}  |  tasks: {s['cfg'].get('tasks')}  |  model: {s['cfg']['model']}"
          f"  |  reasoning: {s['cfg'].get('reasoning')}\n")
    print("## Outcomes\n")
    for ag in s["agents"]:
        o = "source (scripted)" if ag["agent"] == 0 else outcome(ag) if ag.get("label") else "-"
        L = ag.get("label") or {}
        print(f"- agent {ag['agent']} `{ag['issue']}`: **{o}**, steps {ag['steps']}, visible pass {L.get('visible')}, "
              f"correct-tests pass {L.get('truth_spec', L.get('truth'))}, changed {list(L.get('changed', {}))}")
    print("\n## Board (all posts)\n")
    for p in s.get("board", []):
        print(f"- tick {p['tick']}, agent {p['author']} ({p['kind']}):\n\n{fence(p['text'])}\n")
    for ag in s["agents"][1:]:
        print(f"\n---\n\n## Agent {ag['agent']}: `{ag['issue']}`\n")
        for e in ag["log"]:
            ev = e.get("event")
            if ev == "push":
                print(f"\n**[step {e['step']}] board push:** " + " | ".join(
                    f"agent {p['author']} ({p['kind']}): {p['text'][:200]}…" for p in e.get("posts", [])) + "\n")
            elif ev == "step":
                print(f"\n### step {e['step']}\n")
                if e.get("reasoning"):
                    print("*reasoning:*\n\n> " + e["reasoning"].strip().replace("\n", "\n> ") + "\n")
                if e.get("text"):
                    print(f"*says:* {e['text'].strip()}\n")
                for c in e.get("calls", []):
                    out = str(c.get("output", ""))
                    print(f"- `{c['name']}({c['arguments'][:300]})`")
                    if out:
                        print("\n" + fence(out[:CUT] + (" …" if len(out) > CUT else "")) + "\n")
    retries = sum(e.get("event") == "retry" for ag in s["agents"] for e in ag["log"])
    print(f"\n---\n\nAPI retries in this session (mostly 429): {retries}")


if __name__ == "__main__":
    main(sys.argv[1])
