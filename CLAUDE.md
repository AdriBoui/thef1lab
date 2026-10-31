# thef1lab — F1 data platform (BigQuery + dbt)

End-to-end data platform on Formula 1 data, built as a Data Engineering portfolio project on a
100%-free-tier GCP stack.

**This is a standalone project.** It is unrelated to `AGI_CDC` and `AGI_API`, which live in
sibling folders under `~/Documents/`. Do not read or edit files outside this directory unless
explicitly asked.

See `README.md` for the full GCP setup and rationale — this file covers only what an agent needs.

## Pipeline

```
OpenF1 API → ingestion/ (Python) → BigQuery raw_openf1 → dbt/ → staging (views) → marts (tables) → dashboard/ (Streamlit) or Looker Studio
```

Orchestrated by a single GitHub Actions workflow: `.github/workflows/pipeline.yml` (daily cron
currently disabled — manual `workflow_dispatch` only, see Status).

## Layout

| Path | Role |
|---|---|
| `ingestion/` | `openf1_client.py` (API), `load_to_bigquery.py` (loader), `config.py`, `run.py` (entry point) |
| `dbt/models/staging/` | Typed/cleaned views over raw |
| `dbt/models/marts/` | `dim_*` / `fact_*` tables + dbt tests |
| `dbt/seeds/`, `dbt/macros/` | Seed data and macros |
| `dashboard/` | Streamlit app on the marts. SQL only in `queries.py` (column `CONTRACT`); run from repo root |
| `docs/` | Looker guide, Notion write-up |
| `.venv/` | Project virtualenv (note the dot — differs from the other two projects) |
| `credentials/` | GCP service-account key — **never commit, never print** |

## Deliberate design choices (don't "fix" these)

- **Full refresh, not incremental** — one season is tens of MB; truncate-and-reload is simpler
  and BigQuery load jobs are free. Incremental is a documented v2, not an oversight.
- **No raw telemetry** (`car_data`, `location`) — ~3.7 Hz per driver would burn the free tier.
- **Current season only** — scope decision; `SEASON_YEAR` is the parameter to change.

## Points scoring

`fact_race_results` holds Grand Prix **and** Sprint results: OpenF1 tags both
`session_type = 'Race'`, only `session_name` differs. Each uses its own seed
(`f1_points_system`, `f1_sprint_points_system`). Filter on `session_name = 'Race'`
when you need Grand Prix only.

## Conventions

- Datasets are in region **EU**: `raw_openf1`, `staging`, `marts`.
- This is the only one of the three projects under git — commit here, and only when asked.
- `.env` holds local config; `.env.example` documents it. Never commit `.env` or `credentials/`.
- Run dbt from the `dbt/` directory.

## Mode de travail

The user is learning Data Engineering through this project. In every session:

- **Explique avant d'agir.** Before each step, say what you are about to do and why (the DE
  concept behind it), then **wait for the user's go-ahead** before running commands or editing files.
- **Une branche et une PR par fonctionnalité.** Never work directly on `main`: create a
  `feat/…` / `fix/…` / `docs/…` branch, commit there, and open a PR on `AdriBoui/thef1lab`.
  Commit and push only when the user asks.
- **Jamais de secrets dans git.** Never commit, print, or paste `.env`, `credentials/`,
  `.streamlit/secrets.toml` or any service-account JSON. Check `git status` before each commit.
- Prefer letting the user type commands and code themselves when it helps them learn; explain
  errors rather than silently fixing them.

## Status — 31 October 2026

The repo is on GitHub (`AdriBoui/thef1lab`, branch `main`). PR #1 (`feat/dashboard`) is merged: a
Streamlit dashboard (`dashboard/`), the sprint-points fix and `fact_stints`. The Actions workflow
exists but its cron is **disabled** — it is `workflow_dispatch` only until the GCP secrets are set.

The local folder was recreated from GitHub, so the **local secrets are gone**: no `.env`, no
`credentials/` key. `~/.dbt/profiles.yml` still points its `keyfile` at the old, deleted path
(`~/Documents/thef1lab/credentials/…`). The `.venv` has the dashboard deps but **not dbt**.
`docs/guide-looker.md` (Looker Studio) is still valid as an alternative to Streamlit.

Roadmap agreed with the user (one branch + PR per step):

1. Recreate `.env` and the service-account key — secrets management, GCP IAM
2. Run the pipeline locally (ingestion, `dbt seed`, `dbt run`, `dbt test`)
3. Point the dashboard at the real data
4. Add the user's own views / charts (Streamlit, Plotly, analytical SQL)
5. Publish on Streamlit Community Cloud (read-only `f1-dashboard` service account)
6. Re-enable the GitHub Actions cron

Older notes and open items also live in Notion:
(lien privé retiré — demander au propriétaire)

### Costs — already verified, no need to recompute

- Weekly cron (~120 min/month): free on a private repo (2 000 free minutes/month) and on a public
  one (unlimited). Public is **not** required for it to be free — it matters for the portfolio.
- OpenF1 is free; BigQuery holds ~10.7 MB against 10 GB free, and queries stay far under the
  1 TB/month free tier.
- Once on GitHub the cron runs on GitHub's runners — the Mac does not need to be on.
- dbt Cloud: set aside for now, worth revisiting later.
