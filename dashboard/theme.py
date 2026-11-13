"""Habillage Streamlit : CSS de l'app et gabarit Plotly.

Les couleurs viennent de `palette.py`, partagé avec le générateur de page statique.
"""
import plotly.graph_objects as go
import plotly.io as pio

from palette import (TARMAC, SURFACE, LINE, TEXT, MUTED, PURPLE, GREEN, LOSS,
                     RED, FONT, TYRES)  # noqa: F401  (réexportés : app.py fait T.GREEN, etc.)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&display=swap');
.stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp label, .stApp button p, .stApp div[data-baseweb] {{ font-family: {FONT} !important; }}
.stApp {{ background: {TARMAC}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2rem; max-width: 1280px; }}
h1, h2, h3 {{ font-weight: 700; letter-spacing: -0.01em; color: {TEXT}; }}
[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {LINE}; }}

.brand {{ display:flex; align-items:baseline; gap:.6rem; margin-bottom:.2rem; }}
.brand .mark {{ width:14px; height:28px; background:{RED}; transform:skewX(-18deg); }}
.brand h1 {{ font-size:2.1rem; font-weight:900; margin:0; padding:0; }}
.sub {{ color:{MUTED}; margin:0 0 1.2rem 0; }}

.headline {{ font-size:1.35rem; line-height:1.45; color:{TEXT}; max-width:62ch;
             margin:.4rem 0 1.4rem 0; }}
.headline b {{ font-weight:700; }}
.muted {{ color:{MUTED}; }}

/* Tour de classement façon diffusion TV */
.tower {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:10px; padding:.4rem 0; }}
.tower .row {{ display:grid; grid-template-columns: 2.2rem 4px 3.4rem 1fr auto 4.2rem;
               align-items:center; gap:.6rem; padding:.34rem .9rem; font-variant-numeric: tabular-nums; }}
.tower .row:nth-child(odd) {{ background: rgba(255,255,255,0.018); }}
.tower .pos {{ color:{MUTED}; text-align:right; font-weight:600; }}
.tower .bar {{ height:1.1rem; border-radius:2px; }}
.tower .code {{ font-weight:700; letter-spacing:.02em; }}
.tower .name {{ color:{MUTED}; font-size:.88rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.tower .pts {{ font-weight:700; text-align:right; }}
.tower .gap {{ color:{MUTED}; text-align:right; font-size:.88rem; }}
.tower .row.lead .pos {{ color:{PURPLE}; }}
.tower .row.lead .gap {{ color:{PURPLE}; }}

.section-title {{ font-size:1.05rem; font-weight:700; color:{TEXT}; margin:1.2rem 0 .2rem 0; }}
.note {{ color:{MUTED}; font-size:.85rem; margin-bottom:.4rem; }}

.stTabs [data-baseweb="tab-list"] {{ gap:1.6rem; border-bottom:1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ font-size:1.02rem; font-weight:600; padding:.5rem 0; }}
.stTabs [aria-selected="true"] {{ color:{TEXT}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:{TEXT}; }}

.demo {{ border:1px solid {LINE}; border-left:3px solid #F5C518; background:{SURFACE};
         padding:.6rem .9rem; border-radius:6px; color:{MUTED}; font-size:.9rem; margin-bottom:1rem; }}
@media (max-width: 700px) {{
  .tower .row {{ grid-template-columns: 1.8rem 4px 3rem 1fr 3.6rem; }}
  .tower .gap {{ display:none; }}
  .headline {{ font-size:1.12rem; }}
}}
</style>
"""

pio.templates["timing"] = go.layout.Template(layout=dict(
    font=dict(family=FONT, color=TEXT, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE, tickcolor=LINE),
    yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE, tickcolor=LINE),
    hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE, font=dict(family=FONT, color=TEXT)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED)),
    margin=dict(l=10, r=10, t=10, b=10),
))
pio.templates.default = "timing"
