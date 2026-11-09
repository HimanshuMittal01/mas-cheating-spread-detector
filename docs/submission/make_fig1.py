# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Figures for the submission, computed from the committed result tables and the Line C session files.

    uv run docs/submission/make_fig1.py     # writes docs/submission/fig1.png and fig2.png

fig1: share of SESSIONS in which a teammate used the posted shortcut, by condition (Wilson 95% over sessions).
fig2: among teammates who saw the shortcut with a wrong test in place, shortcut use by whether their code was already correct.
"""
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "swarm2"))
from analyze_mx import load, outcome  # noqa: E402

POSTED, CONTROL, INK, GRID = "#2a78d6", "#a3a29b", "#2b2b28", "#e4e3dd"
OUT = Path(__file__).parent
t = lambda v: v in ("True", "1", "1.0")  # noqa: E731


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return max(0, c - h), min(1, c + h)


def sessions(rows, key, hit):
    return len({r[key] for r in rows if hit(r)}), len({r[key] for r in rows})


# experiments 6 (factor screen) and 7 (realistic repo): committed agent tables
B = list(csv.DictReader(open(ROOT / "results/main/agents_regraded.csv")))
D = [a for a in csv.DictReader(open(ROOT / "results/realism/agents.csv")) if a["agent"] != "0"]
b_on = sessions([a for a in B if a["control"] != "True" and a["method"] == "1.0"], "rollout", lambda a: a["hook"] == "1")
b_off = sessions([a for a in B if a["control"] != "True" and a["method"] == "0.0"], "rollout", lambda a: a["hook"] == "1")
b_none = sessions([a for a in B if a["control"] == "True"], "rollout", lambda a: a["hook"] == "1")
d = {arm: sessions([a for a in D if a["arm"] == arm], "rollout", lambda a: t(a["hook"])) for arm in ("real", "scripted", "control")}


# experiment 8 (reasoning on): session files
def c_sessions(run, planted):
    ss = [s for s in load(ROOT / "runs2_ec2" / run) if s["planted"] == planted]
    return sum(any(outcome(a) == "hook" for a in s["agents"][1:]) for s in ss), len(ss)


rows = [  # (label, shortcut on the board?, sessions with a user, sessions); exp. 4 and 5 counts from docs/storyline.md
    ("4  Honest fix possible: real cheating agent", True, 0, 29),
    ("4  Honest fix possible: control", False, 0, 29),
    ("5  Wrong test + merge rule (pilot): post", True, 2, 3),
    ("5  Wrong test + merge rule (pilot): no post", False, 0, 2),
    ("6  Post with the shortcut's code", True, *b_on),
    ("6  Post without the code", True, *b_off),
    ("6  No post", False, *b_none),
    ("7  Realistic repo: real cheating agent", True, *d["real"]),
    ("7  Realistic repo: fixed post", True, *d["scripted"]),
    ("7  Realistic repo: no source agent", False, *d["control"]),
    ("8  Reasoning on, wrong test: pilot post", True, *c_sessions("px-qwen", True)),
    ("8  Reasoning on, wrong test: post", True, *c_sessions("mx-wrong", True)),
    ("8  Reasoning on, wrong test: harmless post", False, *c_sessions("mx-wrong", False)),
    ("8  Reasoning on, correct tests: post", True, *c_sessions("mx-correct", True)),
    ("8  Reasoning on, correct tests: harmless post", False, *c_sessions("mx-correct", False)),
]

fig, ax = plt.subplots(figsize=(8.6, 0.36 * len(rows) + 1.0))
y = list(range(len(rows)))[::-1]
for yi, (lab, posted, k, n) in zip(y, rows):
    lo, hi = wilson(k, n)
    ax.barh(yi, k / n, height=0.62, color=POSTED if posted else CONTROL)
    ax.plot([lo, hi], [yi, yi], color=INK, lw=1)
    ax.text(hi + 0.012, yi, f"{k} of {n}", va="center", fontsize=8, color=INK)
ax.set_yticks(y, [r[0] for r in rows], fontsize=8.5)
ax.set_xlim(0, 1.08)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_xlabel("Sessions in which a teammate used the posted shortcut (Wilson 95% interval)", fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.6)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", labelsize=8)
for b in (1.5, 3.5, 6.5, 9.5):  # separators between experiments
    ax.axhline(len(rows) - 1 - b, color="#c9c8c1", lw=0.6)
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=POSTED), plt.Rectangle((0, 0), 1, 1, color=CONTROL)],
          labels=["shortcut on the board", "control"], fontsize=8, frameon=False, loc="upper right")
fig.savefig(OUT / "fig1.png", dpi=200, bbox_inches="tight")


# figure 2: shortcut use by code correctness (wrong test in place, shortcut on the board)
def split(rows, ok, hook):
    good = [r for r in rows if ok(r)]
    bad = [r for r in rows if not ok(r)]
    return (sum(hook(r) for r in good), len(good)), (sum(hook(r) for r in bad), len(bad))


b2 = split([a for a in B if a["control"] != "True"], lambda a: a["spec_ok"] == "True", lambda a: a["hook"] == "1")
d2 = split([a for a in D if a["arm"] != "control"], lambda a: t(a["spec_ok"]), lambda a: t(a["hook"]))
c_ag = [a for run in ("px-qwen", "mx-wrong") for s in load(ROOT / "runs2_ec2" / run) if s["planted"] for a in s["agents"][1:]]
c2 = split(c_ag, lambda a: a["label"].get("truth_spec", a["label"]["truth"]), lambda a: outcome(a) == "hook")
groups = [("Exp. 6\nfactor screen", b2), ("Exp. 7\nrealistic repo", d2), ("Exp. 8\nreasoning on", c2)]

fig, ax = plt.subplots(figsize=(6.4, 3.0))
w = 0.36
for i, (lab, (good, bad)) in enumerate(groups):
    for j, ((k, n), col, name) in enumerate(((good, POSTED, "code already correct"), (bad, CONTROL, "code still wrong"))):
        x = i + (j - 0.5) * w
        lo, hi = wilson(k, n)
        ax.bar(x, k / n, width=w * 0.92, color=col, label=name if i == 0 else None)
        ax.plot([x, x], [lo, hi], color=INK, lw=1)
        ax.text(x, hi + 0.012, f"{k} of {n}", ha="center", fontsize=8, color=INK)
ax.set_xticks(range(len(groups)), [g[0] for g in groups], fontsize=8.5)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_ylabel("Teammates who used the shortcut", fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(labelsize=8)
ax.set_ylim(0, 0.66)
ax.legend(fontsize=8, frameon=False, loc="upper left")
fig.savefig(OUT / "fig2.png", dpi=200, bbox_inches="tight")
print("fig1 rows:", [(r[0], r[2], r[3]) for r in rows])
print("fig2:", [(g[0].split()[1], g[1]) for g in groups])
