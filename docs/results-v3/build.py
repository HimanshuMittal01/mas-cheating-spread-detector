"""Build docs/results-v3/results-v3.html (+ PDF via headless Chrome) from results/main and runs3/main.

  python docs/results-v3/build.py            # HTML
  then: chrome --headless=new --virtual-time-budget=15000 --print-to-pdf=... results-v3.html
"""
import json
import math
import re
from pathlib import Path

import markdown
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"  # dataviz reference slots 1-4 (validated)
GREY, INK, INK2, GRID = "#a3a29c", "#0b0b0b", "#52514e", "#e6e5e0"
FONT = dict(family="Segoe UI, Arial, sans-serif", size=12, color=INK)
FACTORS = ["method", "success", "persuade", "sources", "coordinate", "test_wording", "push_every", "model", "mode",
           "auto_results"]
LABEL = {"method": "Method (hook code)", "success": "Success claim", "persuade": "Persuade style",
         "sources": "3 posters", "coordinate": "Team request", "test_wording": "\"Don't modify tests\"",
         "push_every": "Push every 5 steps", "model": "Model B (Qwen)", "mode": "Network mode",
         "auto_results": "Auto results"}
DISGUISED = {("C10_r0", 1), ("S03_r1", 1), ("S07_r2", 1), ("S09_r2", 1), ("S16_r1", 1), ("S20_r0", 2),
             ("S20_r2", 3), ("S24_r0", 3), ("S24_r1", 3), ("S26_r1", 1)}  # hand-checked, see EXPERIMENT_LOG


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def base_layout(fig, h, **kw):
    fig.update_layout(width=680, height=h, font=FONT, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=150, r=20, t=30, b=45), **kw)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=GRID, ticks="")
    fig.update_yaxes(showgrid=False, linecolor=GRID, ticks="")
    return fig


def load():
    d = pd.read_csv(ROOT / "results" / "main" / "agents.csv")
    d["rid_agent"] = list(zip(d["rollout"], d["agent"]))
    return d


def ame_table():
    import sys
    sys.path.insert(0, str(ROOT))
    from swarm2.analyze_v3 import fit_ame
    d = load()
    return fit_ame(d[~d["control"]])


def f_levels(d):
    """Tamper share at level 0 and level 1 of each factor (dumbbell with Wilson 95% intervals)."""
    m = d[~d["control"]]
    order = list(ame_table().index)[::-1]
    fig = go.Figure()
    for lv, col, name in ((0, ORANGE, "Level 0 (off)"), (1, BLUE, "Level 1 (on)")):
        xs, lo, hi = [], [], []
        for f in order:
            g = m[m[f] == lv]["tamper"]
            k, n = int(g.sum()), len(g)
            a, b = wilson(k, n)
            xs.append(100 * k / n), lo.append(100 * (k / n - a)), hi.append(100 * (b - k / n))
        fig.add_trace(go.Scatter(
            x=xs, y=[LABEL[f] for f in order], mode="markers", name=name,
            marker=dict(size=9, color=col, line=dict(color="white", width=2)),
            error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=col, thickness=1.5, width=0),
            hovertemplate="%{y}: %{x:.1f}%<extra>" + name + "</extra>"))
    for f in order:
        g0, g1 = m[m[f] == 0]["tamper"].mean() * 100, m[m[f] == 1]["tamper"].mean() * 100
        fig.add_shape(type="line", x0=g0, x1=g1, y0=LABEL[f], y1=LABEL[f], line=dict(color=GRID, width=3),
                      layer="below")
    fig.add_vline(x=0, line=dict(color=INK2, width=1))
    base_layout(fig, 320, legend=dict(orientation="h", y=1.09, x=0, font=dict(size=12)))
    fig.update_xaxes(title="Tamper share of honest agents (%), 144 agents per level", range=[-1, 26], ticksuffix="%")
    return fig


def f_settings(d):
    """Distribution of tamper share over settings: dot stacks per group."""
    g = d.groupby("setting").agg(k=("tamper", "sum"), n=("tamper", "size"), method=("method", "first"),
                                 control=("control", "first")).reset_index()
    g["share"] = 100 * g["k"] / g["n"]
    g["group"] = g.apply(lambda r: "No post (controls)" if r["control"] else
                         ("Post, method on" if r["method"] == 1 else "Post, method off"), axis=1)
    groups = ["No post (controls)", "Post, method off", "Post, method on"]
    fig = go.Figure()
    for gi, name in enumerate(groups):
        sub = g[g["group"] == name].sort_values("share")
        ys, xs, texts = [], [], []
        for share, grp in sub.groupby("share"):
            for j, (_, r) in enumerate(grp.iterrows()):
                xs.append(share)
                ys.append(gi + (j - (len(grp) - 1) / 2) * 0.052)
                texts.append(f"{r['setting']}: {r['k']}/{r['n']} tampered")
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=name, showlegend=False,
                                 marker=dict(size=9, color=BLUE if gi == 2 else (GREY if gi == 0 else ORANGE),
                                             line=dict(color="white", width=1.5)),
                                 text=texts, hovertemplate="%{text}<extra></extra>"))
        fig.add_annotation(x=88, y=gi, xanchor="right", text=f"mean {sub['share'].mean():.1f}%",
                           showarrow=False, font=dict(size=11, color=INK2))
    base_layout(fig, 320)
    fig.update_yaxes(tickvals=[0, 1, 2], ticktext=["No post<br>(16 controls)", "Post, method off<br>(16 settings)",
                                                   "Post, method on<br>(16 settings)"], range=[-0.6, 2.6])
    fig.update_xaxes(title="Tamper share in one setting (%): main settings 9 agents each, controls 3",
                     range=[-3, 89], ticksuffix="%")
    fig.update_layout(height=290)
    return fig


def f_ame():
    r = ame_table()
    order = list(r.index)[::-1]
    lo = [(r.loc[f, "ame"] - 1.96 * r.loc[f, "se"]) * 100 for f in order]
    hi = [(r.loc[f, "ame"] + 1.96 * r.loc[f, "se"]) * 100 for f in order]
    cols = [BLUE if (r.loc[f, "p_holm"] < 0.05 and r.loc[f, "ame"] > 0) else
            (INK2 if r.loc[f, "p_holm"] < 0.1 else GREY) for f in order]
    x = [r.loc[f, "ame"] * 100 for f in order]
    fig = go.Figure(go.Scatter(
        x=x, y=[LABEL[f] for f in order], mode="markers", showlegend=False,
        marker=dict(size=10, color=cols, line=dict(color="white", width=2)),
        error_x=dict(type="data", symmetric=False, array=[h - v for h, v in zip(hi, x)],
                     arrayminus=[v - l for v, l in zip(x, lo)], color=GREY, thickness=1.5, width=0),
        customdata=[[r.loc[f, "p_holm"]] for f in order],
        hovertemplate="%{y}: %{x:+.1f} pts, Holm p = %{customdata[0]:.3f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK2, width=1))
    for f in order:
        if r.loc[f, "p_holm"] < 0.1:
            fig.add_annotation(x=hi[order.index(f)], y=LABEL[f], xanchor="left", xshift=6, showarrow=False,
                               text=f"Holm p = {r.loc[f, 'p_holm']:.3f}", font=dict(size=11, color=INK2))
    base_layout(fig, 340)
    fig.update_xaxes(title="Average marginal effect on tamper (points), 95% CI, clustered by rollout",
                     range=[-12, 34], ticksuffix="")
    return fig


def f_routes(d):
    m = d[~d["control"]].copy()

    def route(r):
        if r["tamper"]:
            return "Pasted the posted hook" if r["root_conftest"] else "Edited test files or data"
        if r["special_case"]:
            return "Special-case, disguised" if r["rid_agent"] in DISGUISED else "Special-case, open"
        return None
    m["route"] = m.apply(route, axis=1)
    routes = [("Pasted the posted hook", BLUE), ("Edited test files or data", ORANGE),
              ("Special-case, open", AQUA), ("Special-case, disguised", YELLOW)]
    models = [("qwen3.5-397b", "Qwen3.5-397B"), ("glm-5.2", "GLM-5.2")]
    fig = go.Figure()
    for name, col in routes:
        ks = [int(((m["model_name"] == mid) & (m["route"] == name)).sum()) for mid, _ in models]
        fig.add_trace(go.Bar(y=[lab for _, lab in models], x=ks, name=name, orientation="h",
                             marker=dict(color=col, line=dict(color="white", width=2)),
                             text=[str(k) if k else "" for k in ks], textposition="inside",
                             insidetextanchor="middle", textfont=dict(color=INK, size=12),
                             hovertemplate="%{y}, " + name + ": %{x} agents<extra></extra>"))
    base_layout(fig, 250, barmode="stack", bargap=0.45,
                legend=dict(orientation="h", y=1.25, x=0, font=dict(size=11), traceorder="normal"))
    fig.update_layout(margin=dict(l=110, r=20, t=50, b=45))
    fig.update_xaxes(title="Honest agents who cheated (of 144 per model, rollouts with a post)", range=[0, 28])
    return fig


def chart_html(fig, div):
    return (f'<div class="chart" id="{div}"></div><script>Plotly.newPlot("{div}", {fig.to_json()}.data, '
            f'{fig.to_json()}.layout, {{staticPlot: true, displayModeBar: false}});</script>')


def appendix(d):
    rows = []
    s = pd.read_csv(ROOT / "docs" / "design-v3" / "settings.csv")
    g = d.groupby("setting").agg(t=("tamper", "sum"), c=("cheat_any", "sum"), n=("tamper", "size"))
    short = {"yes": "Y", "no": "–", "report": "rep", "persuade": "pers", "none": "·", "neutral": "neu", "ban": "ban",
             "10 steps": "10", "5 steps": "5", "model A": "GLM", "model B": "Qwen", "one-hop": "1-hop",
             "network": "net", "on": "on", "off": "off"}
    cols = ["method", "success", "persuade", "sources", "coordinate", "test_wording", "push_every", "model", "mode",
            "auto_results"]
    head = "".join(f"<th>{c.replace('_', ' ')}</th>" for c in ["setting"] + cols) + \
        "<th>tamper</th><th>any cheat</th>"
    for _, r in s.iterrows():
        x = g.loc[r["setting"]]
        rows.append("<tr>" + f"<td>{r['setting']}</td>" + "".join(f"<td>{short.get(str(r[c]), r[c])}</td>"
                                                                    for c in cols)
                    + f"<td><b>{x.t}</b>/{x.n}</td><td>{x.c}/{x.n}</td></tr>")
    return f'<table class="appx"><tr>{head}</tr>{"".join(rows)}</table>'


CSS = """@page{size:A4;margin:14mm 15mm}
body{font-family:"Segoe UI",Arial,sans-serif;font-size:10.3pt;line-height:1.4;color:#1e1e1e}
h1{font-size:20pt;margin:0 0 4px;border-bottom:3px solid #1e1e1e;padding-bottom:6px}
h2{font-size:13.5pt;margin:16px 0 6px;color:#1971c2;break-after:avoid}
p,li{margin:3px 0} ul,ol{padding-left:20px;margin:4px 0}
table{border-collapse:collapse;width:100%;margin:6px 0 8px;font-size:9.5pt;break-inside:avoid}
th,td{border:1px solid #ced4da;padding:4px 7px;text-align:left;vertical-align:top}
th{background:#f1f3f5} tr:nth-child(even) td{background:#fafbfc}
table.appx{font-size:7.5pt;break-inside:auto} table.appx td,table.appx th{padding:1px 4px;line-height:1.25}
code{font-family:Consolas,monospace;font-size:9pt;background:#f1f3f5;padding:0 3px;border-radius:3px}
.fig{margin:8px 0;break-inside:avoid;text-align:center}.fig svg{width:100%;height:auto;max-height:82mm}
.chart{margin:6px auto;width:680px;break-inside:avoid}
.cap{font-size:9pt;color:#52514e;margin:0 0 10px;break-before:avoid}"""


def main():
    d = load()
    charts = {"levels": f_levels(d), "settings": f_settings(d), "ame": f_ame(), "routes": f_routes(d)}
    md = (HERE / "results-v3.md").read_text(encoding="utf-8")
    md = re.sub(r"!\[([^\]]*)\]\((figures/[^)]+)\)", lambda m: '<div class="fig">' + re.sub(
        r'width="\d+" height="\d+"', "", (HERE / m.group(2)).read_text(encoding="utf-8")) + "</div>", md)
    html = markdown.markdown(md, extensions=["tables"])
    for k, fig in charts.items():
        html = html.replace(f"<p>[[chart:{k}]]</p>", chart_html(fig, k))
    appx = ('<div style="break-before:page"></div><h2>Appendix: the 48 settings and their results</h2>'
            "<p>S01–S32: 3 repeats × 3 honest agents = 9 agents. C01–C16: no post, 3 agents. "
            "Y = block on, – = off, · = no post.</p>" + appendix(d))
    out = (f'<!doctype html><html><head><meta charset="utf-8"><title>Design v3 results</title>'
           f"<style>{CSS}</style><script>{get_plotlyjs()}</script></head><body>{html}{appx}</body></html>")
    (HERE / "results-v3.html").write_text(out, encoding="utf-8")
    print("wrote", HERE / "results-v3.html")


if __name__ == "__main__":
    main()
