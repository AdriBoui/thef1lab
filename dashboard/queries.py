"""
Requêtes SQL du dashboard, branchées sur les marts dbt de thef1lab.

Chaque requête doit renvoyer EXACTEMENT les colonnes de CONTRACT : l'app ne
dépend que de ce contrat. Si un modèle dbt change, c'est ici qu'on adapte.

Placeholders : {project}, {marts}, {season}
{season} vaut une année (ex. 2026) ou, par défaut, la dernière saison chargée.
"""

CONTRACT = {
    "races":     ["session_key", "meeting_key", "round", "meeting_name",
                  "country_name", "circuit_short_name", "date_start", "year"],
    "drivers":   ["driver_number", "name_acronym", "full_name",
                  "team_name", "team_colour"],
    # Grand Prix ET Sprints (session_name = 'Race' ou 'Sprint')
    "results":   ["session_key", "meeting_key", "session_name",
                  "driver_number", "position", "points", "dnf"],
    "laps":      ["session_key", "driver_number", "lap_number",
                  "lap_duration", "is_pit_out_lap"],
    "pit_stops": ["session_key", "driver_number", "lap_number", "stop_duration"],
    "stints":    ["session_key", "driver_number", "stint_number",
                  "compound", "lap_start", "lap_end"],
    # Qualif → grille réelle (pénalités incluses) → arrivée, Grand Prix uniquement
    "grid":      ["session_key", "driver_number", "qualifying_position",
                  "grid_position", "finish_position", "grid_penalty_places",
                  "positions_gained"],
}

QUERIES = {
    # Un Grand Prix par ligne (hors Sprints et hors événements annulés)
    "races": """
        select
            s.session_key,
            s.meeting_key,
            row_number() over (order by s.date_start) as round,
            m.meeting_name,
            m.country_name,
            m.circuit_short_name,
            s.date_start,
            s.year
        from `{project}.{marts}.dim_session` s
        join `{project}.{marts}.dim_meeting` m using (meeting_key)
        where s.session_name = 'Race'
          and not coalesce(m.is_cancelled, false)
          and s.year = {season}
    """,

    "drivers": """
        select driver_number, name_acronym, full_name, team_name, team_colour
        from `{project}.{marts}.dim_driver`
    """,

    "results": """
        select r.session_key, r.meeting_key, r.session_name,
               r.driver_number, r.position, r.points, r.dnf
        from `{project}.{marts}.fact_race_results` r
        join `{project}.{marts}.dim_session` s using (session_key)
        where s.year = {season}
    """,

    "laps": """
        select l.session_key, l.driver_number, l.lap_number,
               l.lap_duration, l.is_pit_out_lap
        from `{project}.{marts}.fact_laps` l
        join `{project}.{marts}.dim_session` s using (session_key)
        where s.session_name = 'Race' and s.year = {season}
    """,

    # stop_duration = temps à l'arrêt (travail de l'équipe, ~2 à 3 s)
    "pit_stops": """
        select p.session_key, p.driver_number, p.lap_number, p.stop_duration
        from `{project}.{marts}.fact_pit_stops` p
        join `{project}.{marts}.dim_session` s using (session_key)
        where s.session_name = 'Race' and s.year = {season}
          and p.stop_duration is not null
    """,

    # Optionnel : si fact_stints n'existe pas encore, le graphe pneus est masqué
    "stints": """
        select t.session_key, t.driver_number, t.stint_number,
               t.compound, t.lap_start, t.lap_end
        from `{project}.{marts}.fact_stints` t
        join `{project}.{marts}.dim_session` s using (session_key)
        where s.session_name = 'Race' and s.year = {season}
    """,

    # La grille vient de l'endpoint OpenF1 starting_grid, pas du classement des
    # qualifs : une pénalité moteur fait partir un pilote plus loin (voir dbt).
    "grid": """
        select g.session_key, g.driver_number, g.qualifying_position,
               g.grid_position, g.finish_position, g.grid_penalty_places,
               g.positions_gained
        from `{project}.{marts}.fact_grid_vs_result` g
        join `{project}.{marts}.dim_session` s using (session_key)
        where g.session_name = 'Race' and s.year = {season}
    """,
}

LATEST_SEASON = "(select max(year) from `{project}.{marts}.dim_session`)"
