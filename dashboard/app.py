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
cond = D["conditions"]
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


def _runs(df, col):
    """Plages de tours contiguës où col est vrai (pour ombrer le graphique)."""
    out, start = [], None
    for lap, on in zip(df.lap_number, df[col]):
        if on and start is None:
            start = lap
        elif not on and start is not None:
            out.append((start, prev))
            start = None
        prev = lap
    if start is not None:
        out.append((start, prev))
    return out


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

tab_champ, tab_race, tab_cond, tab_duel = st.tabs(
    ["Championnat", "Course", "Conditions", "Duel"])

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

# ---------- Conditions ----------
# Météo rattachée au tour par jointure as-of, Safety Car reconstitué depuis le
# journal des commissaires — les deux viennent de dbt (fact_lap_conditions).
with tab_cond:
    if cond.empty:
        st.info("Pas encore de conditions de course : lance `dbt run` pour créer "
                "`marts.fact_lap_conditions`.")
    else:
        c_labels = {k: v for k, v in labels.items() if k in set(cond.session_key)}
        skc = st.selectbox("Grand Prix", list(c_labels)[::-1], format_func=c_labels.get,
                           key="cond_race")
        rc = cond[cond.session_key == skc]

        green = rc[~rc.under_safety_car & ~rc.is_outlier_lap]
        # Compter des TOURS, pas des lignes : une ligne est un couple pilote-tour,
        # donc sommer les booléens multiplierait tout par le nombre de pilotes.
        wet_n = green.loc[green.is_wet, "lap_number"].nunique()
        sc_n = rc.loc[rc.under_safety_car, "lap_number"].nunique()
        bits = []
        if sc_n:
            bits.append(f"<b>{sc_n} tours neutralisés</b> par un Safety Car ou un VSC")
        if wet_n:
            bits.append(f"<b>{wet_n} tours sous la pluie</b>")
        tmax = rc.track_temperature.max()
        piste = f"piste jusqu’à {tmax:.0f} °C" if pd.notna(tmax) else "température de piste indisponible"
        phrase = ", ".join(bits + [piste])
        st.markdown(f'<p class="headline">{phrase[0].upper() + phrase[1:]}.</p>',
                    unsafe_allow_html=True)

        # Rythme du peloton tour par tour, avec les périodes marquées
        st.markdown('<div class="section-title">La course, tour par tour</div>'
                    '<div class="note">Temps médian du peloton. Les bandes grises sont les '
                    'périodes neutralisées, les bandes bleues la pluie.</div>',
                    unsafe_allow_html=True)
        # Les tours aberrants (suspension au drapeau rouge) ne sont pas des temps
        # au tour : un seul écrase l'échelle du graphique.
        per_lap = (rc[~rc.is_outlier_lap].groupby("lap_number")
                     .agg(median=("lap_duration", "median"),
                          track=("track_temperature", "median"),
                          wet=("is_wet", "max"), sc=("under_safety_car", "max"))
                     .reset_index().sort_values("lap_number"))
        if per_lap.empty:
            st.caption("Pas de tour chronométré pour cette course.")
        else:
            fig = go.Figure()
            for col, colour_, label in ((("sc"), "rgba(139,147,161,0.22)", "Neutralisé"),
                                        (("wet"), "rgba(0,103,173,0.30)", "Pluie")):
                for a, b in _runs(per_lap, col):
                    fig.add_vrect(x0=a - 0.5, x1=b + 0.5, fillcolor=colour_,
                                  line_width=0, layer="below")
            fig.add_scatter(x=per_lap.lap_number, y=per_lap["median"], mode="lines",
                            line=dict(color=T.TEXT, width=2), name="Rythme médian",
                            hovertemplate="Tour %{x} : %{y:.2f} s<extra></extra>")
            fig.add_scatter(x=per_lap.lap_number, y=per_lap.track, mode="lines", yaxis="y2",
                            line=dict(color=T.PURPLE, width=2, dash="dot"),
                            name="Température piste",
                            hovertemplate="Tour %{x} : %{y:.1f} °C<extra></extra>")
            fig.update_layout(xaxis_title="Tour",
                              yaxis=dict(title="Temps au tour (s)"),
                              yaxis2=dict(title="Piste (°C)", overlaying="y", side="right",
                                          showgrid=False),
                              legend=dict(orientation="h", y=1.1, x=0))
            chart(fig, 400)

        # Le coût de la pluie, comparé DANS la même course : le circuit est neutralisé.
        st.markdown('<div class="section-title">Ce que coûte la pluie</div>'
                    '<div class="note">Temps médian d’un tour mouillé face à un tour sec, '
                    'dans la même course et hors tours neutralisés. Comparer à l’intérieur '
                    'd’une course évite de comparer Monaco à Spa.</div>',
                    unsafe_allow_html=True)
        g = cond[~cond.under_safety_car & ~cond.is_outlier_lap]
        comp = (g.groupby(["session_key", "is_wet"]).lap_duration.median().unstack()
                 .rename(columns={True: "pluie", False: "sec"}))
        comp["tours_pluie"] = g[g.is_wet].groupby("session_key").size()
        comp = comp.dropna(subset=["pluie", "sec"])
        if comp.empty:
            st.caption("Aucune course n’a eu à la fois des tours mouillés et des tours secs.")
        else:
            comp = comp.assign(cout=comp.pluie - comp.sec).sort_values("cout")
            fig = go.Figure(go.Bar(
                # La taille d'échantillon va sur l'étiquette, pas dans l'infobulle :
                # une barre bâtie sur 11 tours ne doit pas peser comme une barre
                # bâtie sur 150.
                x=comp.cout,
                y=[f"{labels.get(k, k)} — {int(n)} tours-pilotes" for k, n in
                   zip(comp.index, comp.tours_pluie)],
                orientation="h",
                marker_color=T.TYRES["INTERMEDIATE"],
                text=comp.cout.map("+{:.1f} s".format), textposition="outside", cliponaxis=False,
                customdata=comp[["tours_pluie"]],
                hovertemplate="%{x:+.2f} s par tour<br>%{customdata[0]:.0f} tours-pilotes sous la pluie"
                              "<extra></extra>"))
            fig.update_layout(xaxis=dict(title="Secondes perdues par tour",
                                         range=[0, comp.cout.max() * 1.25]),
                              yaxis=dict(showgrid=False))
            chart(fig, 70 * len(comp) + 90)
            st.markdown(
                f'<div class="note">Seulement <b>{len(comp)} course(s)</b> ont connu les deux '
                'régimes : la pluie de la saison est tombée hors des courses ou les a couvertes '
                'entièrement. L’écart ci-dessus est une estimation sur petit échantillon, et le '
                'drapeau de pluie d’OpenF1 est binaire — il ne dit rien de l’intensité.</div>',
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
