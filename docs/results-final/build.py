"""Build docs/results-final/results-final.{html,pdf}: corrected main run + realism check.

  python docs/results-final/build.py   (then print to PDF with headless Chrome, see EXPERIMENT_LOG)
Charts read results/main/agents_regraded.csv and results/realism/agents.csv directly.
"""
import json
import math
import re
import sys
from pathlib import Path

import markdown
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
from plotly.offline import get_plotlyjs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from swarm2.analyze_v3 import FACTORS, holm  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"  # dataviz slots 1-4 (validated)
GREY, INK, INK2, GRID = "#a3a29c", "#0b0b0b", "#52514e", "#e6e5e0"
FONT = dict(family="Segoe UI, Arial, sans-serif", size=12, color=INK)
LABEL = {"method": "Method (hook code)", "success": "Success claim", "persuade": "Persuade style",
         "sources": "3 posters", "coordinate": "Team request", "test_wording": "\"Don't modify tests\"",
         "push_every": "Push every 5 steps", "model": "Model B (Qwen)", "mode": "Network mode",
         "auto_results": "Auto results"}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def base(fig, h, **kw):
    fig.update_layout(width=680, height=h, font=FONT, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=150, r=20, t=30, b=45), **kw)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID, ticks="")
    fig.update_yaxes(showgrid=False, linecolor=GRID, ticks="")
    return fig


def main_df():
    return pd.read_csv(ROOT / "results" / "main" / "agents_regraded.csv")


def f_main_routes(d):
    """What the old 'tamper' + special-case labels really were, by method block."""
    m = d[~d.control]
    other = ((m.tamper == 1) & (m.hook == 0) & (m.test_restore == 0)).astype(int)
    rows = [("Used the posted hook", m.hook, BLUE), ("Restored wrong test to correct value", m.test_restore, AQUA),
            ("Green suite, wrong code", m.broken_green, ORANGE), ("Other test change", other, GREY)]
    groups = [("Method block off", m.method == 0), ("Method block on", m.method == 1)]
    fig = go.Figure()
    for name, col, color in rows:
        ks = [int(col[sel].sum()) for _, sel in groups]
        fig.add_trace(go.Bar(y=[g for g, _ in groups], x=ks, name=name, orientation="h",
                             marker=dict(color=color, line=dict(color="white", width=2)),
                             text=[str(k) if k else "" for k in ks], textposition="inside", insidetextanchor="middle",
                             textfont=dict(color=INK, size=12), hovertemplate="%{y}: %{x}<extra>" + name + "</extra>"))
    base(fig, 240, barmode="stack", bargap=0.45, legend=dict(orientation="h", y=1.32, x=0, font=dict(size=11)))
    fig.update_layout(margin=dict(l=130, r=20, t=60, b=45))
    fig.update_xaxes(title="Honest agents (of 144 per row, main run)")
    return fig


def lpm(df, y, fs):
    X = sm.add_constant(df[fs].astype(float))
    f = sm.OLS(df[y].astype(float), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.rollout)[0]})
    o = pd.DataFrame({"ame": f.params, "se": f.bse, "p": f.pvalues}).drop("const")
    o["p_holm"] = pd.Series(holm(o.p.to_dict()))
    return o.sort_values("ame")


def f_main_hook_effects(d):
    o = lpm(d[~d.control], "hook", list(FACTORS))
    x = list(o.ame * 100)
    lo, hi = list((o.ame - 1.96 * o.se) * 100), list((o.ame + 1.96 * o.se) * 100)
    cols = [BLUE if (p < 0.05 and a > 0) else GREY for p, a in zip(o.p_holm, o.ame)]
    fig = go.Figure(go.Scatter(x=x, y=[LABEL[f] for f in o.index], mode="markers", showlegend=False,
                               marker=dict(size=10, color=cols, line=dict(color="white", width=2)),
                               error_x=dict(type="data", symmetric=False, array=[h - v for h, v in zip(hi, x)],
                                            arrayminus=[v - l for v, l in zip(x, lo)], color=GREY, thickness=1.5, width=0),
                               hovertemplate="%{y}: %{x:+.1f} pts<extra></extra>"))
    for f, h in zip(o.index, hi):
        if o.loc[f, "p_holm"] < 0.15:
            fig.add_annotation(x=h, y=LABEL[f], xanchor="left", xshift=6, showarrow=False,
                               text=f"Holm p = {o.loc[f, 'p_holm']:.3f}", font=dict(size=11, color=INK2))
    fig.add_vline(x=0, line=dict(color=INK2, width=1))
    base(fig, 330)
    fig.update_xaxes(title="Effect on hook use (points), 95% CI, linear model clustered by rollout", range=[-10, 26])
    return fig


def f_realism(r):
    arms = [("control", "Control (all honest)"), ("real", "Real LLM cheater"), ("scripted", "Scripted post")]
    fig = go.Figure()
    for col, name, color in (("hook", "Used the hook", BLUE), ("broken_green", "Green suite, wrong code", ORANGE)):
        xs, lo, hi = [], [], []
        for a, _ in arms:
            g = r[r.arm == a][col]
            k, n = int(g.sum()), len(g)
            w = wilson(k, n)
            xs.append(100 * k / n), lo.append(100 * (k / n - w[0])), hi.append(100 * (w[1] - k / n))
        fig.add_trace(go.Scatter(x=xs, y=[lab for _, lab in arms], mode="markers", name=name,
                                 marker=dict(size=10, color=color, line=dict(color="white", width=2)),
                                 error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=color,
                                              thickness=1.5, width=0),
                                 hovertemplate="%{y}: %{x:.1f}%<extra>" + name + "</extra>"))
    fig.update_traces(selector=dict(name="Used the hook"), marker_symbol="circle")
    base(fig, 250, legend=dict(orientation="h", y=1.18, x=0))
    fig.update_xaxes(title="Share of honest agents (%), 95% intervals, 120 agents per arm", range=[-1, 30],
                     ticksuffix="%")
    return fig


def f_exposure(r, roll):
    rr = roll[roll.arm == "real"]
    g = r[r.arm == "real"]
    steps = [("Rollouts where the cheater posted the method", int(rr.a0_retransmits.sum()), len(rr), "rollouts"),
             ("Honest agents who saw a cheater post before finishing", int(g.exposed.sum()), len(g), "agents"),
             ("…of those, used the hook", int(g[g.exposed].hook.sum()), int(g.exposed.sum()), "agents")]
    fig = go.Figure(go.Bar(y=[s[0] for s in steps][::-1], x=[100 * s[1] / s[2] for s in steps][::-1], orientation="h",
                           marker=dict(color=BLUE, line=dict(color="white", width=2)),
                           text=[f"{s[1]}/{s[2]} {s[3]}" for s in steps][::-1], textposition="outside",
                           textfont=dict(color=INK, size=12), hovertemplate="%{y}: %{x:.0f}%<extra></extra>"))
    base(fig, 220, showlegend=False)
    fig.update_layout(margin=dict(l=330, r=60, t=20, b=45))
    fig.update_xaxes(title="Share (%)", range=[0, 115], ticksuffix="%")
    return fig


def chart_html(fig, div):
    j = fig.to_json()
    return (f'<div class="chart" id="{div}"></div><script>(function(){{var f={j};'
            f'Plotly.newPlot("{div}", f.data, f.layout, {{staticPlot: true, displayModeBar: false}});}})();</script>')


CSS = """@page{size:A4;margin:14mm 15mm}
body{font-family:"Segoe UI",Arial,sans-serif;font-size:10.3pt;line-height:1.4;color:#1e1e1e}
h1{font-size:20pt;margin:0 0 4px;border-bottom:3px solid #1e1e1e;padding-bottom:6px}
h2{font-size:13.5pt;margin:16px 0 6px;color:#1971c2;break-after:avoid}
p,li{margin:3px 0} ul,ol{padding-left:20px;margin:4px 0}
table{border-collapse:collapse;width:100%;margin:6px 0 8px;font-size:9.5pt;break-inside:avoid}
th,td{border:1px solid #ced4da;padding:4px 7px;text-align:left;vertical-align:top}
th{background:#f1f3f5} tr:nth-child(even) td{background:#fafbfc}
code{font-family:Consolas,monospace;font-size:9pt;background:#f1f3f5;padding:0 3px;border-radius:3px}
blockquote{margin:6px 0;padding:6px 10px;border-left:4px solid #e03131;background:#fff5f5}
.fig{margin:8px 0;break-inside:avoid;text-align:center}.fig svg{width:100%;height:auto;max-height:82mm}
.chart{margin:6px auto;width:680px;break-inside:avoid}
.cap{font-size:9pt;color:#52514e;margin:0 0 10px;break-before:avoid}"""


def main():
    d = main_df()
    r = pd.read_csv(ROOT / "results" / "realism" / "agents.csv")
    g = json.loads((ROOT / "results" / "realism" / "regrade.json").read_text())
    r["spec_ok"] = [g.get(f"{a}|{b}|spec") for a, b in zip(r.rollout, r.agent)]
    r["broken_green"] = ((r.any_cheat == 1) & (r.spec_ok == False)).astype(int)  # noqa: E712
    roll = pd.read_csv(ROOT / "results" / "realism" / "rollouts.csv")
    charts = {"main_routes": f_main_routes(d), "main_hook": f_main_hook_effects(d), "realism": f_realism(r),
              "exposure": f_exposure(r, roll)}
    md = (HERE / "results-final.md").read_text(encoding="utf-8")
    md = re.sub(r"!\[([^\]]*)\]\((figures/[^)]+)\)", lambda m: '<div class="fig">' + re.sub(
        r'width="\d+" height="\d+"', "", (HERE / m.group(2)).read_text(encoding="utf-8")) + "</div>", md)
    html = markdown.markdown(md, extensions=["tables"])
    for k, fig in charts.items():
        html = html.replace(f"<p>[[chart:{k}]]</p>", chart_html(fig, k))
    out = (f'<!doctype html><html><head><meta charset="utf-8"><title>Cheating spread: results</title>'
           f"<style>{CSS}</style><script>{get_plotlyjs()}</script></head><body>{html}</body></html>")
    (HERE / "results-final.html").write_text(out, encoding="utf-8")
    print("wrote", HERE / "results-final.html")


if __name__ == "__main__":
    main()
