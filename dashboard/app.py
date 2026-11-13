import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import theme as T
from data import is_demo, load_all, settings

st.set_page_config(page_title="thef1lab", page_icon="🏁", layout="wide")
st.markdown(T.CSS, unsafe_allow_html=True)

# ---------- Données ----------
try:
    D, warnings = load_all()
except Exception as e:
    st.error(f"Impossible de charger les données. {e}\n\n"
             "Vérifie les requêtes dans `queries.py` et les droits du service account.")
    st.stop()

races, drivers, results = D["races"], D["drivers"], D["results"]
laps, pits, stints = D["laps"], D["pit_stops"], D["stints"]
tyres = D["tyres"]
done_check = races.session_key.isin(results.session_key)
if races.empty or not done_check.any():
    st.info("Aucun Grand Prix couru pour cette saison. Lance le pipeline puis clique sur « Rafraîchir les données ».")
    st.stop()

drv = drivers.set_index("driver_number")
done = races[races.session_key.isin(results.session_key)]
cfg = settings()
season = int(races.year.max())


def code(n): return drv.at[n, "name_acronym"] if n in drv.index else str(n)
def name(n): return drv.at[n, "full_name"] if n in drv.index else str(n)
def colour(n): return drv.at[n, "team_colour"] if n in drv.index else T.MUTED


def second_driver_of_team(numbers):
    """Le 2e pilote de chaque équipe est tracé en pointillés (même couleur)."""
    seen, dashed = set(), set()
    for n in numbers:
        team = drv.at[n, "team_name"] if n in drv.index else n
        if team in seen:
            dashed.add(n)
        else:
            seen.add(team)
    return dashed


def chart(fig, height=380):
    fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f"**Saison {season}**")
    st.caption("Source : mode démo (données fictives)" if is_demo()
               else f"Source : BigQuery `{cfg['project']}.{cfg['marts']}`")
    st.caption(f"{len(done)} Grand(s) Prix couru(s) sur {len(races)}. Points des Sprints inclus.")
    if st.button("Rafraîchir les données", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    for w in warnings:
        st.warning(w)

# ---------- En-tête ----------
st.markdown('<div class="brand"><div class="mark"></div><h1>thef1lab</h1></div>'
            f'<p class="sub">Saison {season} de Formule 1, des données OpenF1 au tableau de bord.</p>',
            unsafe_allow_html=True)
if is_demo():
    st.markdown('<div class="demo">Mode démo : données fictives. Ajoute tes credentials BigQuery '
                '(voir README) pour afficher tes vraies données.</div>', unsafe_allow_html=True)

tab_champ, tab_race, tab_tyres, tab_duel = st.tabs(
    ["Championnat", "Course", "Pneus", "Duel"])

# ---------- Classement ----------
# Grand Prix + Sprints, rattachés à la manche du week-end
res = results.merge(races[["meeting_key", "round", "meeting_name", "country_name"]], on="meeting_key")
res_gp = res[res.session_name == "Race"]
standings = (res.groupby("driver_number", as_index=False).points.sum()
             .merge(res_gp.groupby("driver_number", as_index=False)
                    .agg(wins=("position", lambda p: (p == 1).sum()), best=("position", "min")),
                    on="driver_number", how="left")
             .sort_values(["points", "wins", "best"], ascending=[False, False, True])
             .reset_index(drop=True))
standings["pos"] = standings.index + 1
order = standings.driver_number.tolist()
# Libellés de course, partagés par plusieurs onglets
labels = {r.session_key: f"Manche {r.round} : {r.meeting_name}" for r in done.itertuples()}

with tab_champ:
    lead, second = standings.iloc[0], standings.iloc[1]
    gap = int(lead.points - second.points)
    st.markdown(
        f'<p class="headline"><b>{name(lead.driver_number)}</b> mène le championnat avec '
        f'{gap} point{"s" if gap != 1 else ""} d’avance sur {name(second.driver_number)} '
        f'après {len(done)} course{"s" if len(done) > 1 else ""}.</p>', unsafe_allow_html=True)

    left, right = st.columns([5, 7], gap="large")
    with left:
        rows = []
        for _, r in standings.iterrows():
            n = r.driver_number
            g = "Leader" if r.pos == 1 else f"−{int(lead.points - r.points)}"
            team = drv.at[n, "team_name"] if n in drv.index else ""
            rows.append(
                f'<div class="row{" lead" if r.pos == 1 else ""}"><span class="pos">{r.pos}</span>'
                f'<span class="bar" style="background:{colour(n)}"></span>'
                f'<span class="code">{code(n)}</span><span class="name">{team}</span>'
                f'<span class="pts">{int(r.points)}</span><span class="gap">{g}</span></div>')
        st.markdown(f'<div class="tower">{"".join(rows)}</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-title">Évolution des points</div>'
                    '<div class="note">Les 6 premiers en couleur. Clique sur un pilote de la légende pour le masquer.</div>',
                    unsafe_allow_html=True)
        cum = (res.pivot_table(index="round", columns="driver_number", values="points", aggfunc="sum")
               .fillna(0).cumsum())
        top = order[:6]
        dashed = second_driver_of_team(top)
        fig = go.Figure()
        for n in reversed(order):
            is_top = n in top
            fig.add_scatter(
                x=cum.index, y=cum[n], name=code(n), mode="lines",
                line=dict(color=colour(n) if is_top else T.LINE, width=2.6 if is_top else 1.2,
                          dash="dot" if n in dashed else "solid"),
                showlegend=is_top, hovertemplate=f"{code(n)} : %{{y:.0f}} pts<extra>Manche %{{x}}</extra>")
        fig.update_layout(xaxis_title="Manche", yaxis_title=None, legend=dict(orientation="h", y=-0.18),
                          hovermode="closest")
        chart(fig, 430)

        st.markdown('<div class="section-title">Constructeurs</div>', unsafe_allow_html=True)
        teams = (res.merge(drivers, on="driver_number").groupby(["team_name", "team_colour"], as_index=False)
                 .points.sum().sort_values("points"))
        fig = go.Figure(go.Bar(x=teams.points, y=teams.team_name, orientation="h",
                               marker_color=teams.team_colour, text=teams.points.astype(int),
                               textposition="outside", cliponaxis=False,
                               hovertemplate="%{y} : %{x:.0f} pts<extra></extra>"))
        fig.update_layout(xaxis=dict(showgrid=False, visible=False), yaxis=dict(showgrid=False))
        chart(fig, 34 * len(teams) + 30)

# ---------- Course ----------
with tab_race:
    sk = st.selectbox("Course", list(labels)[::-1], format_func=labels.get)
    rr = results[results.session_key == sk].sort_values("position")
    podium = rr.driver_number.head(3).tolist()
    race = done.set_index("session_key").loc[sk]
    if len(podium) >= 3:
        st.markdown(f'<p class="headline"><b>{name(podium[0])}</b> remporte le {race.meeting_name} '
                    f'devant {name(podium[1])} et {name(podium[2])}.</p>', unsafe_allow_html=True)

    finish_order = rr.driver_number.tolist()
    pick = st.multiselect("Pilotes", finish_order, default=podium, format_func=code, max_selections=6)

    # Rythme tour par tour
    st.markdown('<div class="section-title">Rythme en course</div>'
                '<div class="note">Hors tour 1 et tours de sortie des stands. Point violet : meilleur tour de la course.</div>',
                unsafe_allow_html=True)
    lp = laps[(laps.session_key == sk) & (laps.lap_number > 1) & (~laps.is_pit_out_lap.fillna(False).astype(bool))]
    lp = lp[lp.lap_duration < lp.lap_duration.median() * 1.07]
    if lp.empty or not pick:
        st.caption("Pas de données de tours pour cette sélection.")
    else:
        fig, dashed = go.Figure(), second_driver_of_team(pick)
        for n in pick:
            d = lp[lp.driver_number == n].sort_values("lap_number")
            fig.add_scatter(x=d.lap_number, y=d.lap_duration, name=code(n), mode="lines",
                            line=dict(color=colour(n), width=2, dash="dot" if n in dashed else "solid"),
                            hovertemplate=f"{code(n)} tour %{{x}} : %{{y:.3f}} s<extra></extra>")
        best = lp.loc[lp.lap_duration.idxmin()]
        fig.add_scatter(x=[best.lap_number], y=[best.lap_duration], mode="markers", showlegend=False,
                        marker=dict(color=T.PURPLE, size=11, line=dict(color=T.TARMAC, width=2)),
                        hovertemplate=f"Meilleur tour : {code(best.driver_number)} %{{y:.3f}} s<extra></extra>")
        fig.update_layout(xaxis_title="Tour", yaxis_title="Temps au tour (s)",
                          legend=dict(orientation="h", y=-0.2))
        chart(fig, 400)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown('<div class="section-title">Stratégie pneus</div>', unsafe_allow_html=True)
        stn = stints[stints.session_key == sk]
        if stn.empty:
            st.caption("Pas de données de relais pour cette course.")
        else:
            fig, shown = go.Figure(), set()
            for n in finish_order[::-1]:
                for s in stn[stn.driver_number == n].itertuples():
                    comp = str(s.compound).upper()
                    fig.add_bar(y=[code(n)], x=[s.lap_end - s.lap_start + 1], base=[s.lap_start - 1],
                                orientation="h", name=comp.title(), legendgroup=comp,
                                showlegend=comp not in shown,
                                marker=dict(color=T.TYRES.get(comp, T.MUTED), line=dict(color=T.TARMAC, width=2)),
                                hovertemplate=f"{code(n)} : {comp.title()} tours {s.lap_start} à {s.lap_end}<extra></extra>")
                    shown.add(comp)
            fig.update_layout(barmode="stack", xaxis_title="Tour", bargap=0.35,
                              yaxis=dict(showgrid=False), legend=dict(orientation="h", y=1.06, x=0))
            chart(fig, 22 * len(finish_order) + 90)
    with c2:
        st.markdown('<div class="section-title">Arrêts aux stands les plus rapides</div>'
                    '<div class="note">Temps à l’arrêt : le travail de l’équipe, voiture immobile.</div>', unsafe_allow_html=True)
        ps = pits[(pits.session_key == sk) & pits.stop_duration.notna()].nsmallest(10, "stop_duration")[::-1]
        if ps.empty:
            st.caption("Pas d’arrêt enregistré.")
        else:
            cols = [T.PURPLE if i == len(ps) - 1 else colour(n) for i, n in enumerate(ps.driver_number)]
            fig = go.Figure(go.Bar(
                x=ps.stop_duration, y=[f"{code(n)}  tour {l}" for n, l in zip(ps.driver_number, ps.lap_number)],
                orientation="h", marker_color=cols, text=ps.stop_duration.map("{:.2f} s".format),
                textposition="outside", cliponaxis=False, hovertemplate="%{y} : %{x:.2f} s<extra></extra>"))
            fig.update_layout(xaxis=dict(range=[0, ps.stop_duration.max() * 1.15], visible=False),
                              yaxis=dict(showgrid=False))
            chart(fig, 30 * len(ps) + 40)

# ---------- Pneus ----------
# La pente vient de dbt (fact_stint_degradation). Deux mesures : la brute, biaisée
# par l'allègement en carburant, et celle relative au peloton, qui l'annule.
with tab_tyres:
    if tyres.empty:
        st.info("Pas encore de données de dégradation : lance `dbt run` pour créer "
                "`marts.fact_stint_degradation`.")
    else:
        t_labels = {k: v for k, v in labels.items() if k in set(tyres.session_key)}
        skt = st.selectbox("Grand Prix", list(t_labels)[::-1], format_func=t_labels.get,
                           key="tyre_race")
        rac = tyres[(tyres.session_key == skt) & tyres.relative_degradation_s_per_lap.notna()]

        if rac.empty:
            st.caption("Aucun relais assez long pour estimer une pente sur cette course.")
        else:
            w = rac.nlargest(1, "relative_degradation_s_per_lap").iloc[0]
            st.markdown(
                f'<p class="headline">Le relais qui s’est le plus dégradé : '
                f'<b>{name(int(w.driver_number))}</b> en {str(w.compound).title()}, '
                f'{w.relative_degradation_s_per_lap:+.3f} s par tour sur '
                f'{int(w.clean_laps)} tours propres, par rapport au peloton.</p>',
                unsafe_allow_html=True)

        # Jointure par intervalle, côté pandas cette fois : les tours portent un
        # numéro, les relais une plage.
        lp = laps[laps.session_key == skt]
        stn = stints[stints.session_key == skt]
        # Mêmes tours propres que le mart dbt : un Safety Car ralentit tout le
        # peloton sur le même tour, donc on le repère en travers des pilotes.
        field = lp.groupby("lap_number").lap_duration.median()
        green = field[field <= lp.lap_duration.median() * 1.15].index
        lp = lp[lp.lap_number.isin(green)]
        m = lp.merge(stn, on=["session_key", "driver_number"])
        m = m[m.lap_number.between(m.lap_start, m.lap_end - 1) & (m.lap_number > 1)
              & (~m.is_pit_out_lap.fillna(False).astype(bool))]
        if not m.empty:
            m = m.assign(age=m.lap_number - m.lap_start,
                         rel=m.lap_duration - m.lap_number.map(field),
                         comp=m.compound.astype(str).str.upper())
            keep = m.groupby(["driver_number", "stint_number"]).lap_duration.transform("median") * 1.07
            m = m[m.lap_duration <= keep].dropna(subset=["rel"])

        st.markdown('<div class="section-title">Le pneu se dégrade-t-il ?</div>'
                    '<div class="note">Écart au peloton sur le même tour, selon l’âge du pneu. '
                    'Comparer au peloton annule l’allègement en carburant et l’évolution de la piste, '
                    'communs à tout le monde au même instant.</div>', unsafe_allow_html=True)
        if m.empty:
            st.caption("Pas assez de tours propres sur cette course.")
        else:
            fig = go.Figure()
            for comp, g in m.groupby("comp"):
                col = T.TYRES.get(comp, T.MUTED)
                fig.add_scatter(x=g.age, y=g.rel, mode="markers", name=comp.title(),
                                marker=dict(color=col, size=5, opacity=0.35),
                                hovertemplate=f"{comp.title()} : %{{y:+.2f}} s à %{{x}} tours<extra></extra>")
                if len(g) >= 8 and g.age.nunique() > 1:
                    a, b = np.polyfit(g.age, g.rel, 1)
                    xs = np.array([g.age.min(), g.age.max()])
                    fig.add_scatter(x=xs, y=a * xs + b, mode="lines", showlegend=False,
                                    line=dict(color=col, width=3),
                                    hovertemplate=f"{comp.title()} : {a:+.3f} s/tour<extra></extra>")
            # Quelques tours restent très loin du peloton (pluie, tête-à-queue).
            # On cadre sur 98 % des points pour voir la pente, et on l'écrit.
            lo, hi = m.rel.quantile([0.01, 0.99])
            pad = max((hi - lo) * 0.1, 0.3)
            hidden = int((m.rel < lo).sum() + (m.rel > hi).sum())
            fig.update_layout(xaxis_title="Âge du pneu (tours)",
                              yaxis=dict(title="Écart au peloton (s)", range=[lo - pad, hi + pad]),
                              legend=dict(orientation="h", y=1.08, x=0))
            chart(fig, 420)
            if hidden:
                st.markdown(f'<div class="note">Échelle cadrée sur 98 % des tours : '
                            f'{hidden} tour(s) hors cadre, trop loin du peloton pour être lisibles '
                            f'(pluie, tête-à-queue). Ils restent dans le calcul des pentes.</div>',
                            unsafe_allow_html=True)

        st.markdown('<div class="section-title">Sur la saison, par composé</div>'
                    '<div class="note">Chaque point est un relais. Les boîtes se recouvrent largement : '
                    'l’écart entre composés n’est pas tranché par ces données, et une moyenne seule '
                    'le laisserait croire.</div>', unsafe_allow_html=True)
        sea = tyres[tyres.relative_degradation_s_per_lap.notna()]
        if sea.empty:
            st.caption("Pas encore de relais mesurable cette saison.")
        else:
            fig = go.Figure()
            for comp in [c for c in ("SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET")
                         if c in set(sea.compound)]:
                g = sea[sea.compound == comp]
                fig.add_box(x=g.relative_degradation_s_per_lap, name=comp.title(),
                            marker=dict(color=T.TYRES.get(comp, T.MUTED), size=4, opacity=0.5),
                            line=dict(color=T.TYRES.get(comp, T.MUTED)),
                            fillcolor="rgba(0,0,0,0)", boxpoints="all", jitter=0.5, pointpos=0,
                            hovertemplate="%{x:+.3f} s/tour<extra></extra>")
            fig.update_layout(showlegend=False,
                              xaxis=dict(title="Dégradation relative (s/tour)", zeroline=True,
                                         zerolinecolor=T.MUTED),
                              yaxis=dict(showgrid=False))
            chart(fig, 90 * sea.compound.nunique() + 80)

        st.markdown(
            '<div class="note">La pente <b>brute</b> est aussi dans le mart, et elle vaut à peu près '
            'zéro : une F1 s’allège d’environ 1,7 kg par tour, ce qui la fait gagner ~0,05 s — soit '
            'autant que le pneu en perd. Les deux effets s’annulent, et le chiffre brut ne mesure '
            'presque rien. C’est pourquoi tout ce qui est affiché ici est relatif au peloton.</div>',
            unsafe_allow_html=True)


# ---------- Duel ----------
with tab_duel:
    a_col, b_col = st.columns(2)
    a = a_col.selectbox("Pilote A", order, index=0, format_func=name)
    b = b_col.selectbox("Pilote B", order, index=1, format_func=name)
    if a == b:
        st.info("Choisis deux pilotes différents.")
    else:
        h = (res_gp[res_gp.driver_number.isin([a, b])]
             .pivot_table(index=["round", "country_name"], columns="driver_number", values="position")
             .dropna().reset_index())
        ahead = int((h[a] < h[b]).sum()) if not h.empty else 0
        pa = int(standings.set_index("driver_number").at[a, "points"])
        pb = int(standings.set_index("driver_number").at[b, "points"])
        st.markdown(f'<p class="headline"><b>{name(a)}</b> a terminé devant {name(b)} '
                    f'{ahead} fois sur {len(h)} en Grand Prix, avec {pa} points contre {pb}.</p>', unsafe_allow_html=True)

        ca, cb = colour(a), colour(b)
        if ca.upper() == cb.upper():  # coéquipiers
            cb = T.TEXT
        st.markdown('<div class="section-title">Position d’arrivée par course</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for rnd, ya, yb in zip(h["round"], h[a], h[b]):
            fig.add_scatter(x=[rnd, rnd], y=[ya, yb],
                            mode="lines", line=dict(color=T.LINE, width=3), showlegend=False, hoverinfo="skip")
        for n, c in ((a, ca), (b, cb)):
            fig.add_scatter(x=h["round"], y=h[n], mode="markers", name=code(n),
                            marker=dict(color=c, size=12, line=dict(color=T.TARMAC, width=2)),
                            customdata=h["country_name"],
                            hovertemplate=f"{code(n)} : P%{{y}}<extra>%{{customdata}}</extra>")
        fig.update_layout(xaxis_title="Manche", yaxis=dict(autorange="reversed", title="Position", dtick=2),
                          legend=dict(orientation="h", y=1.08, x=0))
        chart(fig, 360)

        st.markdown('<div class="section-title">Écart cumulé tour par tour</div>', unsafe_allow_html=True)
        sk2 = st.selectbox("Course ", list(labels)[::-1], format_func=labels.get, key="duel_race")
        lpd = (laps[(laps.session_key == sk2) & laps.driver_number.isin([a, b])]
               .pivot_table(index="lap_number", columns="driver_number", values="lap_duration").dropna())
        if lpd.empty or a not in lpd or b not in lpd:
            st.caption("Pas assez de tours en commun pour cette course.")
        else:
            gap = (lpd[a] - lpd[b]).cumsum()
            st.markdown(f'<div class="note">Au-dessus de zéro : {code(b)} devant. En dessous : {code(a)} devant.</div>',
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_scatter(x=gap.index, y=gap.clip(lower=0), fill="tozeroy", mode="none",
                            fillcolor=cb, opacity=0.35, showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=gap.index, y=gap.clip(upper=0), fill="tozeroy", mode="none",
                            fillcolor=ca, opacity=0.35, showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=gap.index, y=gap, mode="lines", line=dict(color=T.TEXT, width=2), showlegend=False,
                            hovertemplate="Tour %{x} : %{y:+.2f} s<extra></extra>")
            fig.update_layout(xaxis_title="Tour", yaxis_title="Écart (s)")
            chart(fig, 320)
