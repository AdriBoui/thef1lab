"""Chargement des données : BigQuery si des credentials existent, sinon mode démo."""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

import demo_data
from queries import CONTRACT, LATEST_SEASON, QUERIES

# En local, on réutilise le .env du pipeline (GCP_PROJECT_ID, credentials…)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass


def _secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # pas de secrets.toml
        return {}


def settings() -> dict:
    s = _secrets().get("bigquery", {})
    season = s.get("season", os.getenv("SEASON_YEAR"))
    return {
        "project": s.get("project", os.getenv("GCP_PROJECT_ID", "thef1lab")),
        "marts": s.get("marts_dataset", os.getenv("BQ_MARTS_DATASET", "marts")),
        "location": s.get("location", os.getenv("BQ_LOCATION", "EU")),
        "season": int(season) if season else None,
    }


def is_demo() -> bool:
    if os.getenv("DEMO_MODE", "").lower() in ("1", "true"):
        return True
    return not ("gcp_service_account" in _secrets()
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))


@st.cache_resource
def _client():
    from google.cloud import bigquery
    cfg = settings()
    sa = _secrets().get("gcp_service_account")
    if sa:  # Streamlit Cloud : clé dans les secrets
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(dict(sa))
        return bigquery.Client(project=cfg["project"], credentials=creds,
                               location=cfg["location"])
    # En local : GOOGLE_APPLICATION_CREDENTIALS (lu depuis .env)
    return bigquery.Client(project=cfg["project"], location=cfg["location"])


OPTIONAL = {  # requête: message affiché si sa table manque
    "stints": "Stratégie pneus indisponible : lance `dbt run` pour créer marts.fact_stints.",
    "grid": "Grille de départ indisponible : relance l'ingestion puis `dbt run` "
            "pour créer marts.fact_grid_vs_result.",
}


@st.cache_data(ttl=3600, show_spinner="Chargement des données…")
def load_all() -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Renvoie (tables, avertissements). Cache 1 h = coût BigQuery quasi nul."""
    if is_demo():
        return _clean(demo_data.generate()), []

    cfg = settings()
    params = {"project": cfg["project"], "marts": cfg["marts"]}
    params["season"] = cfg["season"] or LATEST_SEASON.format(**params)

    tables, warnings = {}, []
    for name, sql in QUERIES.items():
        try:
            df = _client().query(sql.format(**params)).to_dataframe()
            missing = set(CONTRACT[name]) - set(df.columns)
            if missing:
                raise ValueError(f"colonnes manquantes : {', '.join(sorted(missing))}")
            tables[name] = df[CONTRACT[name]]
        except Exception as e:
            if name in OPTIONAL:  # une vue en moins plutôt qu'un dashboard en panne
                tables[name] = pd.DataFrame(columns=CONTRACT[name])
                warnings.append(OPTIONAL[name])
            else:
                raise RuntimeError(f"Requête « {name} » en échec : {e}") from e
    return _clean(tables), warnings


def _hex(colours: pd.Series) -> pd.Series:
    return "#" + colours.fillna("888888").astype(str).str.lstrip("#").str.upper()


def _clean(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    d = t["drivers"].copy()
    d["team_colour"] = _hex(d["team_colour"])
    t["drivers"] = d.drop_duplicates("driver_number")
    c = t["constructors"].copy()
    c["team_colour"] = _hex(c["team_colour"])
    c["points"] = pd.to_numeric(c["points"]).fillna(0)
    c["cumulative_points"] = pd.to_numeric(c["cumulative_points"]).fillna(0)
    t["constructors"] = c
    t["races"] = t["races"].sort_values("round").reset_index(drop=True)
    r = t["results"].copy()
    r["points"] = pd.to_numeric(r["points"]).fillna(0)
    r["position"] = pd.to_numeric(r["position"], errors="coerce")
    t["results"] = r
    known = set(t["drivers"].driver_number)  # OpenF1 a parfois des numéros fantômes
    for k in ("laps", "pit_stops", "stints"):
        t[k] = t[k][t[k].driver_number.isin(known)]
    s = t["stints"]
    t["stints"] = s.dropna(subset=["lap_start", "lap_end"])
    g = t["grid"].copy()
    for col in g.columns.drop(["session_key", "driver_number"]):
        g[col] = pd.to_numeric(g[col], errors="coerce")  # NULL = non classé / départ des stands
    t["grid"] = g[g.driver_number.isin(known)]
    return t
