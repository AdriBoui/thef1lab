"""Données fictives mais réalistes, au format du contrat (queries.CONTRACT)."""
import numpy as np
import pandas as pd

TEAMS = {  # nom: (couleur, force)
    "McLaren": ("FF8000", 0.00), "Ferrari": ("E8002D", 0.18),
    "Red Bull Racing": ("3671C6", 0.15), "Mercedes": ("27F4D2", 0.22),
    "Aston Martin": ("229971", 0.75), "Williams": ("64C4FF", 0.65),
    "Racing Bulls": ("6692FF", 0.70), "Alpine": ("0093CC", 0.95),
    "Haas F1 Team": ("B6BABD", 0.80), "Kick Sauber": ("52E252", 0.90),
}
DRIVERS = [  # numéro, acronyme, nom, équipe, talent (plus bas = meilleur)
    (4, "NOR", "Lando Norris", "McLaren", 0.02), (81, "PIA", "Oscar Piastri", "McLaren", 0.04),
    (16, "LEC", "Charles Leclerc", "Ferrari", 0.03), (44, "HAM", "Lewis Hamilton", "Ferrari", 0.12),
    (1, "VER", "Max Verstappen", "Red Bull Racing", -0.12), (22, "TSU", "Yuki Tsunoda", "Red Bull Racing", 0.35),
    (63, "RUS", "George Russell", "Mercedes", 0.02), (12, "ANT", "Kimi Antonelli", "Mercedes", 0.18),
    (14, "ALO", "Fernando Alonso", "Aston Martin", 0.05), (18, "STR", "Lance Stroll", "Aston Martin", 0.25),
    (23, "ALB", "Alexander Albon", "Williams", 0.05), (55, "SAI", "Carlos Sainz", "Williams", 0.10),
    (6, "HAD", "Isack Hadjar", "Racing Bulls", 0.10), (30, "LAW", "Liam Lawson", "Racing Bulls", 0.22),
    (10, "GAS", "Pierre Gasly", "Alpine", 0.08), (43, "COL", "Franco Colapinto", "Alpine", 0.25),
    (31, "OCO", "Esteban Ocon", "Haas F1 Team", 0.10), (87, "BEA", "Oliver Bearman", "Haas F1 Team", 0.15),
    (27, "HUL", "Nico Hulkenberg", "Kick Sauber", 0.08), (5, "BOR", "Gabriel Bortoleto", "Kick Sauber", 0.18),
]
GPS = [  # nom, pays, circuit, tour de référence (s), nombre de tours
    ("Australian Grand Prix", "Australia", "Melbourne", 81.5, 58),
    ("Chinese Grand Prix", "China", "Shanghai", 95.0, 56),
    ("Japanese Grand Prix", "Japan", "Suzuka", 92.0, 53),
    ("Bahrain Grand Prix", "Bahrain", "Sakhir", 96.5, 57),
    ("Saudi Arabian Grand Prix", "Saudi Arabia", "Jeddah", 91.0, 50),
    ("Miami Grand Prix", "United States", "Miami", 90.5, 57),
    ("Emilia Romagna Grand Prix", "Italy", "Imola", 79.5, 63),
    ("Monaco Grand Prix", "Monaco", "Monte Carlo", 74.5, 78),
    ("Spanish Grand Prix", "Spain", "Catalunya", 78.0, 66),
    ("Canadian Grand Prix", "Canada", "Montreal", 75.0, 70),
    ("Austrian Grand Prix", "Austria", "Spielberg", 68.0, 70),
    ("British Grand Prix", "United Kingdom", "Silverstone", 90.0, 52),
    ("Belgian Grand Prix", "Belgium", "Spa-Francorchamps", 108.0, 44),
    ("Hungarian Grand Prix", "Hungary", "Hungaroring", 80.5, 70),
]
POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
SPRINT_POINTS = [8, 7, 6, 5, 4, 3, 2, 1]
SPRINT_ROUNDS = {2, 6, 11}
COMPOUND_PLANS = [["MEDIUM", "HARD"], ["HARD", "MEDIUM"], ["SOFT", "HARD"],
                  ["MEDIUM", "HARD", "SOFT"], ["SOFT", "MEDIUM", "HARD"]]
DEG = {"SOFT": 0.09, "MEDIUM": 0.055, "HARD": 0.035}
OFFSET = {"SOFT": -0.6, "MEDIUM": 0.0, "HARD": 0.45}


def generate(season: int = 2026) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)
    drivers = pd.DataFrame(
        [(n, a, f, t, TEAMS[t][0]) for n, a, f, t, _ in DRIVERS],
        columns=["driver_number", "name_acronym", "full_name", "team_name", "team_colour"],
    )
    races, results, laps, pits, stints = [], [], [], [], []
    start = pd.Timestamp(f"{season}-03-15 05:00", tz="UTC")

    for rnd, (gp, country, circuit, base, n_laps) in enumerate(GPS, start=1):
        sk, mk = 9000 + rnd, 1200 + rnd
        races.append((sk, mk, rnd, gp, country, circuit, start + pd.Timedelta(weeks=2 * rnd), season))
        # pace de course de chaque pilote (s/tour au-dessus de la référence)
        pace = {n: TEAMS[t][1] + s + rng.normal(0, 0.18) for n, _, _, t, s in DRIVERS}
        totals = {}
        for n, *_ in DRIVERS:
            plan = COMPOUND_PLANS[rng.integers(len(COMPOUND_PLANS))]
            cuts = sorted(rng.choice(range(12, n_laps - 8), len(plan) - 1, replace=False))
            bounds = [1, *[c + 1 for c in cuts], n_laps + 1]
            total = 0.0
            for i, comp in enumerate(plan):
                a, b = bounds[i], bounds[i + 1] - 1
                stints.append((sk, n, i + 1, comp, a, b))
                for lap in range(a, b + 1):
                    t = (base + pace[n] + OFFSET[comp] + DEG[comp] * (lap - a)
                         - 0.06 * lap + abs(rng.normal(0, 0.25)))
                    out_lap = lap == a and i > 0
                    if lap == 1:
                        t += 6
                    if out_lap:
                        t += 20
                    total += t
                    laps.append((sk, n, lap, round(t, 3), out_lap))
                if i > 0:
                    pits.append((sk, n, a - 1, round(rng.gamma(9, 0.06) + 1.9, 2)))
            totals[n] = total
        order = sorted(totals, key=totals.get)
        for pos, n in enumerate(order, start=1):
            results.append((sk, mk, "Race", n, pos, POINTS[pos - 1] if pos <= 10 else 0, False))
        if rnd in SPRINT_ROUNDS:
            sprint = sorted(pace, key=lambda n: pace[n] + rng.normal(0, 0.15))
            for pos, n in enumerate(sprint, start=1):
                results.append((sk - 500, mk, "Sprint", n, pos,
                                SPRINT_POINTS[pos - 1] if pos <= 8 else 0, False))

    cols = __import__("queries").CONTRACT
    # Grille fictive : qualif ≈ arrivée bruitée, et quelques pénalités de grille
    grid = []
    for sk in {r[0] for r in results if r[2] == "Race"}:
        finish = {r[3]: r[4] for r in results if r[0] == sk and r[2] == "Race"}
        quali = sorted(finish, key=lambda n: finish[n] + rng.normal(0, 3))
        penalised = set(rng.choice(quali, 2, replace=False))
        starting = [n for n in quali if n not in penalised] + sorted(penalised, key=quali.index)
        for n in finish:
            q, g = quali.index(n) + 1, starting.index(n) + 1
            grid.append((sk, n, q, g, finish[n], g - q, g - finish[n]))
    results = pd.DataFrame(results, columns=cols["results"])
    # Même calcul que mart_constructor_standings (en démo, personne ne change d'équipe)
    constructors = (results.merge(drivers[["driver_number", "team_name", "team_colour"]], on="driver_number")
                    .groupby(["team_name", "team_colour", "meeting_key"], as_index=False).points.sum()
                    .sort_values("meeting_key"))
    constructors["cumulative_points"] = constructors.groupby("team_name").points.cumsum()
    lp = pd.DataFrame(laps, columns=cols["laps"])
    stn = pd.DataFrame(stints, columns=cols["stints"])
    return {
        "tyres": _degradation(lp, stn, cols["tyres"]),
        "grid": pd.DataFrame(grid, columns=cols["grid"]),
        "races": pd.DataFrame(races, columns=cols["races"]),
        "drivers": drivers,
        "results": results,
        "constructors": constructors[cols["constructors"]],
        "laps": lp,
        "pit_stops": pd.DataFrame(pits, columns=cols["pit_stops"]),
        "stints": stn,
    }


def _degradation(lp: pd.DataFrame, stn: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Même recette que le mart dbt : médiane du peloton, puis pente des moindres carrés."""
    field = lp.groupby(["session_key", "lap_number"]).lap_duration.median().rename("field")
    lp = lp.join(field, on=["session_key", "lap_number"])
    rows = []
    for s in stn.itertuples():
        w = lp[(lp.session_key == s.session_key) & (lp.driver_number == s.driver_number)
               & lp.lap_number.between(s.lap_start, s.lap_end - 1)
               & (lp.lap_number > 1) & (~lp.is_pit_out_lap)]
        if w.empty:
            continue
        med = w.lap_duration.median()
        w = w[w.lap_duration <= med * 1.07]
        age, rel = w.lap_number - s.lap_start, w.lap_duration - w.field
        var = float(np.var(age))

        def slope(y):  # cov(y, âge) / var(âge) — NULL sous 8 tours propres
            if len(w) < 8 or var == 0:
                return None
            return round(float(np.cov(age, y, bias=True)[0, 1] / var), 4)

        rows.append((s.session_key, s.driver_number, s.stint_number, s.compound, len(w),
                     int(age.min()), int(age.max()), round(float(med), 3),
                     slope(w.lap_duration), slope(rel), round(float(rel.mean()), 3)))
    return pd.DataFrame(rows, columns=columns)
