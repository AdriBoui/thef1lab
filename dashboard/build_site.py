"""Génère `docs/index.html` : une page statique des marts, publiable sur GitHub Pages.

Pourquoi une page statique plutôt que l'app Streamlit hébergée :
  - elle s'ouvre instantanément (pas de serveur à réveiller) ;
  - aucun secret n'est nécessaire à l'exécution — les chiffres sont dans le HTML ;
  - elle se régénère depuis le même workflow que l'ingestion.

Elle lit les MÊMES requêtes que le dashboard (`queries.py`) : une seule définition
du SQL, deux sorties. Les graphiques sont du SVG écrit à la main — pas de
bibliothèque, donc une page de quelques dizaines de kilooctets.

Usage, depuis la racine du dépôt :
    python dashboard/build_site.py
"""
from __future__ import annotations

import html
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import palette as P  # noqa: E402
from queries import LATEST_SEASON, QUERIES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "index.html"

# Seules les requêtes utiles à la page : les tours bruts ne servent qu'à l'app.
NEEDED = ["races", "drivers", "results", "constructors", "grid", "tyres", "conditions"]


# --------------------------------------------------------------------------- data
def load() -> dict[str, pd.DataFrame]:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    from google.cloud import bigquery

    project = os.getenv("GCP_PROJECT_ID", "thef1lab")
    params = {"project": project, "marts": os.getenv("BQ_MARTS_DATASET", "marts")}
    params["season"] = os.getenv("SEASON_YEAR") or LATEST_SEASON.format(**params)
    client = bigquery.Client(project=project, location=os.getenv("BQ_LOCATION", "EU"))

    out = {}
    for name in NEEDED:
        out[name] = client.query(QUERIES[name].format(**params)).to_dataframe()
        print(f"  {name:12s} {len(out[name]):>6d} lignes")
    return out


def e(x) -> str:
    return html.escape(str(x))


def hexc(c) -> str:
    return "#" + str(c).lstrip("#").upper() if pd.notna(c) else P.MUTED


# ----------------------------------------------------------------------- sections
def prepare(d):
    """Agrégats communs à plusieurs sections."""
    races = d["races"].sort_values("round").reset_index(drop=True)
    drv = d["drivers"].drop_duplicates("driver_number").set_index("driver_number")
    res = d["results"].copy()
    res["points"] = pd.to_numeric(res.points, errors="coerce").fillna(0)
    rounds = dict(zip(races.session_key, races["round"]))
    res["round"] = res.session_key.map(rounds)
    res = res.dropna(subset=["round"])
    res["round"] = res["round"].astype(int)
    n = int(res["round"].max())

    per = res.groupby(["driver_number", "round"], as_index=False).points.sum()
    tot = per.groupby("driver_number", as_index=False).points.sum()
    tot = tot[tot.points > 0].sort_values("points", ascending=False)

    standings = []
    for _, r in tot.iterrows():
        num = int(r.driver_number)
        if num not in drv.index:
            continue
        s = (per[per.driver_number == num].set_index("round").points
             .reindex(range(1, n + 1), fill_value=0).cumsum())
        standings.append(dict(num=num, code=drv.at[num, "name_acronym"],
                              name=drv.at[num, "full_name"], team=drv.at[num, "team_name"],
                              colour=hexc(drv.at[num, "team_colour"]),
                              points=float(r.points), cum=[float(v) for v in s]))
    return dict(races=races, drv=drv, n=n, standings=standings)


def hero(ctx, d):
    s = ctx["standings"]
    lead, second = s[0], s[1]
    laps = int(d["conditions"].shape[0])
    season = int(ctx["races"].year.max())
    tiles = [
        ("Leader", lead["code"], lead["name"]),
        ("Avance", f"{int(lead['points'] - second['points'])}", f"points sur {second['code']}"),
        ("Courses", f"{ctx['n']}", f"sur {len(ctx['races'])} au calendrier"),
        ("Tours analysés", f"{laps:,}".replace(",", " "), "en course, conditions attachées"),
    ]
    cells = "".join(
        f'<div class="stat"><span class="k">{e(k)}</span>'
        f'<span class="num">{e(v)}</span><span class="u">{e(u)}</span></div>'
        for k, v, u in tiles)
    return f'''<div class="brand"><span class="mark"></span><h1>thef1lab</h1></div>
<p class="sub">Saison {season} de Formule 1, reconstruite depuis l’API OpenF1 : ingestion Python,
modélisation dbt sur BigQuery, et cette page générée depuis les mêmes requêtes que l’application.</p>
<div class="stats">{cells}</div>'''


def tower(ctx):
    s, lead = ctx["standings"], ctx["standings"][0]
    rows = []
    for i, p in enumerate(s[:12], 1):
        gap = "Leader" if i == 1 else f"&minus;{int(lead['points'] - p['points'])}"
        rows.append(f'''<div class="row{' lead' if i == 1 else ''}">
  <span class="pos">{i}</span><span class="bar" style="background:{p['colour']}"></span>
  <span class="code">{e(p['code'])}</span>
  <span class="who">{e(p['name'])}<em>{e(p['team'])}</em></span>
  <span class="pts">{int(p['points'])}</span><span class="gap">{gap}</span></div>''')
    return f'<div class="tower">{"".join(rows)}</div>'


def evolution(ctx):
    s, n = ctx["standings"], ctx["n"]
    W, H, L, R, T, B = 980, 440, 52, 132, 20, 38
    mx = max(p["cum"][n - 1] for p in s)
    X = lambda r: L + (r - 1) / max(n - 1, 1) * (W - L - R)
    Y = lambda v: (H - B) - v / mx * (H - B - T)

    seen, dashed = set(), set()
    for p in s:
        if p["team"] in seen:
            dashed.add(p["num"])
        seen.add(p["team"])

    g = []
    for v in range(0, int(mx) + 100, 100):
        g.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W-R}" y2="{Y(v):.1f}" '
                 f'stroke="var(--line)" stroke-width="1"/>')
        g.append(f'<text x="{L-10}" y="{Y(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for r in range(1, n + 1, 4):
        g.append(f'<text x="{X(r):.1f}" y="{H-14}" class="ax" text-anchor="middle">{r}</text>')
    g.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-1}" class="ax" text-anchor="middle">Manche</text>')

    for p in s[6:]:
        pts = " ".join(f"{X(i+1):.1f},{Y(v):.1f}" for i, v in enumerate(p["cum"]))
        g.append(f'<polyline points="{pts}" fill="none" stroke="var(--line)" stroke-width="1.5"/>')
    for p in s[:6]:
        pts = " ".join(f"{X(i+1):.1f},{Y(v):.1f}" for i, v in enumerate(p["cum"]))
        dash = ' stroke-dasharray="6 4"' if p["num"] in dashed else ""
        g.append(f'<polyline points="{pts}" fill="none" stroke="{p["colour"]}" '
                 f'stroke-width="2.5" stroke-linejoin="round"{dash}/>')
        g.append(f'<circle cx="{X(n):.1f}" cy="{Y(p["cum"][n-1]):.1f}" r="3.5" fill="{p["colour"]}"/>')

    lab = sorted(({"y": Y(p["cum"][n - 1]), "p": p} for p in s[:6]), key=lambda x: x["y"])
    for i in range(1, len(lab)):
        lab[i]["y"] = max(lab[i]["y"], lab[i - 1]["y"] + 17)
    for it in lab:
        p = it["p"]
        g.append(f'<text x="{W-R+12}" y="{it["y"]+4:.1f}" class="lbl" fill="{p["colour"]}">'
                 f'{e(p["code"])}<tspan class="lblp" dx="8">{int(p["cum"][n-1])}</tspan></text>')
    return svg(W, H, "".join(g), "Points cumulés par pilote, manche par manche")


def constructors(d):
    c = d["constructors"]
    if c.empty:
        return ""
    tot = (c.groupby("team_name")
            .agg(points=("cumulative_points", "max"), colour=("team_colour", "first"))
            .reset_index().sort_values("points", ascending=False))
    mx = tot.points.max()
    rows = "".join(
        f'''<div class="trow"><span class="tname">{e(r.team_name)}</span>
<span class="track"><span class="fill" style="width:{r.points/mx*100:.1f}%;
background:{hexc(r.colour)}"></span></span>
<span class="tpts">{int(r.points)}</span></div>''' for r in tot.itertuples())
    return f"<div>{rows}</div>"


def grid_section(ctx, d):
    g = d["grid"].copy()
    if g.empty:
        return "", 0
    for col in ("positions_gained", "grid_penalty_places"):
        g[col] = pd.to_numeric(g[col], errors="coerce")
    pen = int((g.grid_penalty_places > 0).sum())
    agg = (g.dropna(subset=["positions_gained"]).groupby("driver_number")
            .agg(avg=("positions_gained", "mean"), races=("positions_gained", "size"))
            .reset_index())
    agg = agg[agg.races >= 3].sort_values("avg", ascending=False)
    drv = ctx["drv"]
    agg = agg[agg.driver_number.isin(drv.index)]
    if agg.empty:
        return "", pen

    W, rowh, L, R, T = 980, 22, 46, 46, 8
    H = T + rowh * len(agg) + 26
    mx = max(abs(agg["avg"].min()), abs(agg["avg"].max()))
    mid = L + (W - L - R) / 2
    half = (W - L - R) / 2
    out = [f'<line x1="{mid}" y1="{T}" x2="{mid}" y2="{T+rowh*len(agg)}" '
           f'stroke="var(--muted)" stroke-width="1"/>']
    for i, r in enumerate(agg.itertuples()):
        y = T + i * rowh
        w = abs(r.avg) / mx * half
        x = mid if r.avg >= 0 else mid - w
        col = P.GREEN if r.avg > 0 else P.LOSS
        out.append(f'<rect x="{x:.1f}" y="{y+4}" width="{w:.1f}" height="{rowh-9}" rx="2" fill="{col}"/>')
        out.append(f'<text x="{L-8}" y="{y+rowh/2+4}" class="ax" text-anchor="end">'
                   f'{e(drv.at[r.driver_number, "name_acronym"])}</text>')
        lx = mid + w + 6 if r.avg >= 0 else mid - w - 6
        anc = "start" if r.avg >= 0 else "end"
        out.append(f'<text x="{lx:.1f}" y="{y+rowh/2+4}" class="val" text-anchor="{anc}">'
                   f'{r.avg:+.1f}</text>')
    out.append(f'<text x="{mid}" y="{H-6}" class="ax" text-anchor="middle">'
               f'Places gagnées en moyenne par Grand Prix</text>')
    return svg(W, H, "".join(out), "Places gagnées en moyenne par pilote"), pen


def tyres_section(d):
    t = d["tyres"].copy()
    if t.empty:
        return "", 0
    t["slope"] = pd.to_numeric(t.relative_degradation_s_per_lap, errors="coerce")
    t = t.dropna(subset=["slope"])
    if t.empty:
        return "", 0
    order = [c for c in ("SOFT", "MEDIUM", "HARD", "INTERMEDIATE") if c in set(t.compound)]
    lo, hi = t.slope.quantile([0.02, 0.98])
    span = max(hi - lo, 1e-6)
    W, L, R, rowh, T = 980, 96, 24, 62, 14
    H = T + rowh * len(order) + 30
    X = lambda v: L + (v - lo) / span * (W - L - R)
    # Les valeurs hors cadre sont ÉCARTÉES, pas ramenées au bord : les coller
    # au bord fabriquerait deux colonnes denses qui n'existent pas.
    inside = t[(t.slope >= lo) & (t.slope <= hi)]
    hidden = len(t) - len(inside)

    out = []
    zero = X(0)
    if lo <= 0 <= hi:
        out.append(f'<line x1="{zero:.1f}" y1="{T}" x2="{zero:.1f}" y2="{T+rowh*len(order)}" '
                   f'stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3"/>')
    for i, comp in enumerate(order):
        g = t[t.compound == comp]
        cy = T + i * rowh + rowh / 2
        col = P.TYRES.get(comp, P.MUTED)
        out.append(f'<text x="{L-12}" y="{cy+4:.1f}" class="ax" text-anchor="end">'
                   f'{e(comp.title())}</text>')
        for j, v in enumerate(inside[inside.compound == comp].slope):
            # Dispersion déterministe : la page doit être identique à chaque génération.
            jit = ((j * 37) % 23 - 11) / 11 * (rowh / 2 - 10)
            out.append(f'<circle cx="{X(v):.1f}" cy="{cy+jit:.1f}" r="2.4" fill="{col}" '
                       f'fill-opacity="0.42"/>')
        med = float(g.slope.median())
        out.append(f'<line x1="{X(med):.1f}" y1="{cy-rowh/2+8:.1f}" x2="{X(med):.1f}" '
                   f'y2="{cy+rowh/2-8:.1f}" stroke="{col}" stroke-width="2.5"/>')
        out.append(f'<text x="{L-12}" y="{cy+18:.1f}" class="small" text-anchor="end">'
                   f'{len(g)} relais</text>')
    for v in (lo, (lo + hi) / 2, hi):
        out.append(f'<text x="{X(v):.1f}" y="{H-12}" class="ax" text-anchor="middle">{v:+.2f}</text>')
    axis = "Secondes perdues par tour d’âge du pneu, relatif au peloton"
    if hidden:
        axis += f" — {hidden} relais hors cadre"
    out.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-1}" class="ax" text-anchor="middle">{e(axis)}</text>')
    return svg(W, H, "".join(out), "Distribution de la dégradation par composé"), len(t)


def conditions_section(ctx, d):
    c = d["conditions"].copy()
    if c.empty:
        return "", 0, 0
    for col in ("under_safety_car", "is_wet", "is_outlier_lap"):
        c[col] = c[col].fillna(False).astype(bool)
    g = c.groupby("session_key").apply(lambda x: pd.Series({
        "laps": x.lap_number.nunique(),
        "sc": x.loc[x.under_safety_car, "lap_number"].nunique(),
        "wet": x.loc[x.is_wet, "lap_number"].nunique(),
    }), include_groups=False).reset_index()
    r = ctx["races"][["session_key", "round", "circuit_short_name"]]
    g = g.merge(r, on="session_key").sort_values("round")
    if g.empty:
        return "", 0, 0

    W, T, BH, B, PAD = 980, 16, 150, 62, 34
    H = T + BH + B
    n = len(g)
    step = (W - 2 * PAD) / n
    bw = min(step * 0.62, 26)
    mx = max(g.sc.max(), 1)
    out = []
    for i, r_ in enumerate(g.itertuples()):
        x = PAD + i * step + (step - bw) / 2
        h = r_.sc / mx * BH
        out.append(f'<rect x="{x:.1f}" y="{T+BH-h:.1f}" width="{bw:.1f}" height="{max(h,1):.1f}" '
                   f'rx="2" fill="{P.MUTED}" fill-opacity="{0.9 if r_.sc else 0.25}"/>')
        if r_.sc:
            out.append(f'<text x="{x+bw/2:.1f}" y="{T+BH-h-5:.1f}" class="small" '
                       f'text-anchor="middle">{int(r_.sc)}</text>')
        if r_.wet:
            out.append(f'<rect x="{x:.1f}" y="{T+BH+4:.1f}" width="{bw:.1f}" height="4" rx="2" '
                       f'fill="{P.TYRES["WET"]}"/>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{T+BH+24:.1f}" class="small" text-anchor="middle" '
                   f'transform="rotate(-50 {x+bw/2:.1f} {T+BH+24:.1f})">'
                   f'{e(r_.circuit_short_name)}</text>')
    return (svg(W, H, "".join(out), "Tours neutralisés et courses sous la pluie"),
            int(g.sc.sum()), int((g.wet > 0).sum()))


def svg(w, h, body, label):
    return (f'<div class="chart"><svg viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{e(label)}">{body}</svg></div>')


# --------------------------------------------------------------------------- page
CSS = """
/* Écran de chronométrage : bandes sombres, données en colonnes, un seul accent. */
:root {
  --tarmac:#14171D; --surface:#1A1F27; --line:#2A303B;
  --text:#E9ECF1; --muted:#8B93A1; --accent:#B36BFF; --brand:#E10600;
  --display:"Titillium Web","Segoe UI",Helvetica,Arial,sans-serif;
  --body:"Inter","Segoe UI",Helvetica,Arial,sans-serif;
  color-scheme: dark;
}
* { box-sizing:border-box }
html,body { margin:0 }
body { background:var(--tarmac); color:var(--text); font-family:var(--body) }
.wrap { max-width:1080px; margin:0 auto;
  padding-left:max(16px, env(safe-area-inset-left, 0px));
  padding-right:max(16px, env(safe-area-inset-right, 0px));
  padding-block:40px 64px }
h1,h2,.code,.pts,.num,.ax,.lbl,.val,.tpts { font-family:var(--display) }
h2 { font-size:1.5rem; font-weight:700; letter-spacing:-.01em; margin:0; text-wrap:balance }
.brand { display:flex; align-items:center; gap:.7rem; margin-bottom:.4rem }
.mark { width:13px; height:30px; background:var(--brand); transform:skewX(-18deg) }
h1 { font-size:2.2rem; font-weight:900; margin:0; letter-spacing:-.02em }
.sub { color:var(--muted); margin:0 0 2.4rem; max-width:64ch; line-height:1.55 }
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:10px; overflow:hidden }
.stat { background:var(--surface); padding:1.1rem 1.2rem }
.stat .k { color:var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.08em }
.num { font-size:2rem; font-weight:900; line-height:1.15; font-variant-numeric:tabular-nums;
  display:block; margin-top:.3rem }
.stat .u { color:var(--muted); font-size:.82rem }
section { margin-top:3.2rem }
.note { color:var(--muted); font-size:.88rem; line-height:1.65; margin:.5rem 0 1.4rem; max-width:70ch }
.note strong { color:var(--text); font-weight:600 }
code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.86em;
  background:#20262F; border-radius:3px; padding:.08em .35em }
.tower { border:1px solid var(--line); border-radius:10px; overflow:hidden }
.row { display:grid; grid-template-columns:2.2rem 4px 3.2rem 1fr auto 4.4rem; align-items:center;
  gap:.75rem; padding:.5rem .9rem; font-variant-numeric:tabular-nums; background:var(--surface) }
.row:nth-child(even) { background:#171C24 }
.pos { color:var(--muted); text-align:right; font-weight:600 }
.bar { height:1.5rem; border-radius:2px }
.code { font-weight:700; letter-spacing:.03em }
.who { font-size:.92rem; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }
.who em { color:var(--muted); font-style:normal; font-size:.82rem; display:block }
.pts { font-weight:700; text-align:right }
.gap { color:var(--muted); text-align:right; font-size:.85rem }
.row.lead .pos, .row.lead .gap { color:var(--accent) }
.chart { border:1px solid var(--line); border-radius:10px; background:var(--surface);
  padding:1rem .6rem .4rem; margin-top:.4rem }
svg { width:100%; height:auto; display:block }
.ax { fill:var(--muted); font-size:12px }
.small { fill:var(--muted); font-size:10px }
.val { fill:var(--text); font-size:11px; font-weight:600 }
.lbl { font-size:13px; font-weight:700 }
.lblp { fill:var(--muted); font-weight:600 }
.trow { display:grid; grid-template-columns:9.5rem 1fr 3.4rem; align-items:center; gap:.9rem;
  padding:.42rem 0; font-variant-numeric:tabular-nums }
.tname { font-size:.9rem; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }
.track { background:#20262F; border-radius:3px; height:1.15rem; overflow:hidden }
.fill { display:block; height:100%; border-radius:3px }
.tpts { font-weight:700; text-align:right }
.pipe { display:flex; flex-wrap:wrap; gap:.5rem; align-items:stretch; margin:1rem 0 1.6rem }
.step { background:var(--surface); border:1px solid var(--line); border-radius:8px;
  padding:.6rem .8rem; font-size:.84rem; min-width:0 }
.step b { display:block; font-family:var(--display); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.07em; color:var(--muted); font-weight:600; margin-bottom:.15rem }
.arrow { align-self:center; color:var(--muted) }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem }
.card { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem }
.card h3 { font-family:var(--display); font-size:.95rem; margin:0 0 .5rem }
.card ul { margin:0; padding-left:1.1rem; color:var(--muted); font-size:.86rem; line-height:1.6 }
footer { margin-top:3.6rem; padding-top:1.4rem; border-top:1px solid var(--line);
  color:var(--muted); font-size:.85rem; line-height:1.6 }
footer a { color:var(--accent) }
@media (max-width:620px) {
  h1 { font-size:1.7rem }
  .row { grid-template-columns:1.8rem 4px 2.9rem 1fr 3.4rem }
  .gap, .who em { display:none }
  .trow { grid-template-columns:7rem 1fr 2.8rem }
}
"""

PIPE = [("Source", "OpenF1 API"), ("Ingestion", "Python, 30 req/min"),
        ("Entrepôt", "BigQuery raw"), ("Transformation", "dbt staging → marts"),
        ("Sortie", "cette page")]


def render(ctx, d):
    grid_svg, penalties = grid_section(ctx, d)
    tyre_svg, n_stints = tyres_section(d)
    cond_svg, sc_laps, wet_races = conditions_section(ctx, d)
    season = int(ctx["races"].year.max())

    pipe = '<span class="arrow">→</span>'.join(
        f'<div class="step"><b>{e(k)}</b>{e(v)}</div>' for k, v in PIPE)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>thef1lab — saison {season}</title>
<meta name="description" content="Pipeline de données Formule 1 : OpenF1, Python, BigQuery, dbt.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&family=Inter:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
{hero(ctx, d)}

<section>
  <h2>Championnat pilotes</h2>
  <p class="note">Points des Grands Prix et des Sprints. OpenF1 étiquette les deux de la même
  façon : seul le barème diffère, et chacun a sa propre table de référence.</p>
  {tower(ctx)}
</section>

<section>
  <h2>L’écart s’est creusé</h2>
  <p class="note">Cumul manche par manche. Les six premiers en couleur d’écurie, le reste du
  plateau en gris. Un coéquipier partage la couleur de son équipe : il est tracé en pointillés.</p>
  {evolution(ctx)}
</section>

<section>
  <h2>Championnat constructeurs</h2>
  <p class="note">L’équipe est enregistrée <strong>au moment de la course</strong>, pas d’après
  l’équipe actuelle du pilote : un transfert en cours de saison laisse les points à l’écurie avec
  laquelle ils ont été marqués. Un test vérifie que la somme par équipe retombe sur le total des
  pilotes.</p>
  {constructors(d)}
</section>

<section>
  <h2>De la grille à l’arrivée</h2>
  <p class="note">La grille vient de l’endpoint <code>starting_grid</code>, pas du classement des
  qualifications : <strong>{penalties} départs</strong> de la saison ont été décalés par une
  pénalité. Déduire la grille des qualifs aurait donc été faux presque partout. Pilotes classés
  dans au moins trois Grands Prix.</p>
  {grid_svg}
</section>

<section>
  <h2>La dégradation des pneus</h2>
  <p class="note">Pente du temps au tour en fonction de l’âge de la gomme, ajustée par moindres
  carrés sur {n_stints} relais. Mesurée <strong>relativement au peloton</strong> : une F1 s’allège
  d’environ 1,7 kg par tour, ce qui la fait gagner autant de temps que le pneu lui en fait perdre,
  et la pente brute ne mesure donc presque rien. Les distributions se recouvrent largement —
  <strong>l’écart entre composés n’est pas tranché par ces données</strong>, et une moyenne seule
  le laisserait croire.</p>
  {tyre_svg}
</section>

<section>
  <h2>Les conditions de course</h2>
  <p class="note">{sc_laps} tours neutralisés par un Safety Car ou un VSC sur la saison, et
  {wet_races} courses touchées par la pluie (trait bleu). Les périodes de neutralisation sont
  reconstituées depuis le journal des commissaires, qui émet des <strong>événements</strong> et non
  des états : il faut les apparier en intervalles.</p>
  {cond_svg}
</section>

<section>
  <h2>Comment c’est fait</h2>
  <div class="pipe">{pipe}</div>
  <div class="cards">
    <div class="card"><h3>Choix assumés</h3><ul>
      <li>Rechargement complet plutôt qu’incrémental : une saison tient en quelques dizaines de Mo.</li>
      <li>Pas de télémétrie brute : 3,7 Hz par pilote épuiserait le palier gratuit.</li>
      <li>Saison en cours uniquement.</li></ul></div>
    <div class="card"><h3>Ce qui est testé</h3><ul>
      <li>Unicité des clés, plages de valeurs, intégrité référentielle.</li>
      <li>Réconciliation : la somme des points par équipe doit retomber sur celle des pilotes.</li>
      <li>Types forcés en staging — l’autodétection avait typé une colonne en texte.</li></ul></div>
    <div class="card"><h3>Limites connues</h3><ul>
      <li>La dégradation est une estimation, pas une mesure.</li>
      <li>Deux courses seulement permettent de comparer mouillé et sec.</li>
      <li>Le drapeau de pluie est binaire : aucune intensité.</li></ul></div>
  </div>
</section>

<footer>
  Données OpenF1 → BigQuery → dbt. Page statique générée par
  <code>dashboard/build_site.py</code> : aucune requête n’est émise à l’ouverture, et aucun secret
  n’est nécessaire pour l’afficher. Le code est sur
  <a href="https://github.com/AdriBoui/thef1lab">GitHub</a>.
</footer>
</div>
</body>
</html>
"""


def main():
    print("Lecture des marts…")
    d = load()
    ctx = prepare(d)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(ctx, d), encoding="utf-8")
    print(f"\nÉcrit : {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
