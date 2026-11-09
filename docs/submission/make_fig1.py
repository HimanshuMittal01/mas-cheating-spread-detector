# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""Figure 1: share of honest agents who used the posted hook / special-cased, by condition, Wilson 95% CIs.

    uv run docs/submission/make_fig1.py     # reads runs2_ec2/mx-* for line C, writes docs/submission/fig1.png
Lines A, B, D are fixed counts from their result docs; line C is computed from the session JSONs.
"""
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "swarm2"))
from analyze_mx import load, outcome  # noqa: E402

POSTED, CONTROL = "#2a78d6", "#a3a29b"


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return max(0, c - h), min(1, c + h)


def line_c(*runs):
    """(planted Counter, n), (control Counter, n) over honest agents 1-3."""
    ss = [s for run in runs if (ROOT / "runs2_ec2" / run).is_dir() for s in load(ROOT / "runs2_ec2" / run)]
    out = []
    for planted in (True, False):
        ags = [ag for s in ss if s["planted"] == planted for ag in s["agents"][1:]]
        out.append((Counter(outcome(a) for a in ags), len(ags)))
    return out


(wp, nwp), (wc, nwc) = line_c("mx-wrong", "mx-wrong2")  # two matched batches (seeds 8 and 9)
(cp, ncp), (cc, ncc) = line_c("mx-correct")

# (label, posted?, hook k, green-suite-wrong-code k (special-casing or test tampering) or None, n)
rows = [
    ("A  open route, Gemma: saw working hook", True, 0, None, 21),
    ("A  open route, Gemma: control", False, 0, None, 87),
    ("B  closed route: post with hook code", True, 15, 10, 144),
    ("B  closed route: post without code", True, 0, 15, 144),
    ("B  closed route: no post", False, 0, 1, 48),
    ("C  Qwen+reasoning, wrong test: post", True, wp["hook"], wp["special_case"] + wp["test_tamper"], nwp),
    ("C  Qwen+reasoning, wrong test: placebo", False, wc["hook"], wc["special_case"] + wc["test_tamper"], nwc),
    ("C  Qwen+reasoning, correct tests: post", True, cp["hook"], cp["special_case"] + cp["test_tamper"], ncp),
    ("C  Qwen+reasoning, correct tests: placebo", False, cc["hook"], cc["special_case"] + cc["test_tamper"], ncc),
    ("D  realistic repo: real LLM cheater", True, 2, 18, 120),
    ("D  realistic repo: scripted post", True, 4, 25, 120),
    ("D  realistic repo: control", False, 0, 14, 120),
]
rows = [r for r in rows if r[4]]  # skip a C cell with no data yet

fig, axes = plt.subplots(1, 2, figsize=(10, 0.42 * len(rows) + 1.3), sharey=True, gridspec_kw={"wspace": 0.06})
y = list(range(len(rows)))[::-1]
for ax, idx, title in ((axes[0], 2, "Used the posted hook"), (axes[1], 3, "Green suite, wrong code (no hook)")):
    for yi, r in zip(y, rows):
        k, n = r[idx], r[4]
        if k is None:
            ax.text(0.005, yi, "not measured", va="center", fontsize=8, color="#77766f")
            continue
        lo, hi = wilson(k, n)
        ax.barh(yi, k / n, height=0.6, color=POSTED if r[1] else CONTROL)
        ax.plot([lo, hi], [yi, yi], color="#2b2b28", lw=1)
        ax.text(hi + 0.01, yi, f"{k}/{n}", va="center", fontsize=8, color="#2b2b28")
    ax.set_xlim(0, 0.7)
    ax.set_title(title, fontsize=10, loc="left")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="x", color="#e4e3dd", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=8.5)
    ax.tick_params(axis="x", labelsize=8)
axes[0].set_yticks(y, [r[0] for r in rows])
for b in (1.5, 4.5, 8.5):  # separators between lines A | B | C | D
    for ax in axes:
        ax.axhline(len(rows) - 1 - b, color="#c9c8c1", lw=0.6)
axes[1].legend(handles=[plt.Rectangle((0, 0), 1, 1, color=POSTED), plt.Rectangle((0, 0), 1, 1, color=CONTROL)],
               labels=["shortcut posted", "control (no post / placebo)"], fontsize=8, frameon=False, loc="lower right")
fig.savefig(Path(__file__).with_name("fig1.png"), dpi=200, bbox_inches="tight")
print("wrote fig1.png", [(r[0], r[2], r[3], r[4]) for r in rows])
