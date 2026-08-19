# thef1lab — F1 data platform (BigQuery + dbt)

End-to-end data platform on Formula 1 data, built as a Data Engineering portfolio project on a
100%-free-tier GCP stack.

**This is a standalone project.** It is unrelated to `AGI_CDC` and `AGI_API`, which live in
sibling folders under `~/Documents/`. Do not read or edit files outside this directory unless
explicitly asked.

See `README.md` for the full GCP setup and rationale — this file covers only what an agent needs.

## Pipeline

```
OpenF1 API → ingestion/ (Python) → BigQuery raw_openf1 → dbt/ → staging (views) → marts (tables) → Looker Studio
```

Orchestrated by a single daily GitHub Actions workflow: `.github/workflows/pipeline.yml`.

## Layout

| Path | Role |
|---|---|
| `ingestion/` | `openf1_client.py` (API), `load_to_bigquery.py` (loader), `config.py`, `run.py` (entry point) |
| `dbt/models/staging/` | Typed/cleaned views over raw |
| `dbt/models/marts/` | `dim_*` / `fact_*` tables + dbt tests |
| `dbt/seeds/`, `dbt/macros/` | Seed data and macros |
| `docs/` | Looker guide, Notion write-up |
| `.venv/` | Project virtualenv (note the dot — differs from the other two projects) |
| `credentials/` | GCP service-account key — **never commit, never print** |

## Deliberate design choices (don't "fix" these)

- **Full refresh, not incremental** — one season is tens of MB; truncate-and-reload is simpler
  and BigQuery load jobs are free. Incremental is a documented v2, not an oversight.
- **No raw telemetry** (`car_data`, `location`) — ~3.7 Hz per driver would burn the free tier.
- **Current season only** — scope decision; `SEASON_YEAR` is the parameter to change.

## Conventions

- Datasets are in region **EU**: `raw_openf1`, `staging`, `marts`.
- This is the only one of the three projects under git — commit here, and only when asked.
- `.env` holds local config; `.env.example` documents it. Never commit `.env` or `credentials/`.
- Run dbt from the `dbt/` directory.

## Status — 19 July 2026

The pipeline runs end to end locally: OpenF1 ingestion → `raw_openf1` → dbt (staging views + mart
tables) → dbt tests passing. `docs/guide-looker.md` is written and covers three visuals (pit-stop
performance by team, championship progression, driver pace), the public-sharing setting, and
embedding into the Notion portfolio page.

**Next steps and open items live in Notion**, not in this file — read it when picking up work on
this project: (lien privé retiré — demander au propriétaire)

### Blocker to know about

The git repo is initialised but has **no commits and no remote**, so the Actions workflow cannot
run — nothing is pushed. A first commit plus a GitHub remote are prerequisites for automating the
pipeline at all. The `.gitignore` is already correct (`.env`, `credentials/`, service-account keys
excluded), so a first commit would be clean. The user has said they don't want git for now: raise it
when the automation step comes up, don't push for it.

### Costs — already verified, no need to recompute

- Weekly cron (~120 min/month): free on a private repo (2 000 free minutes/month) and on a public
  one (unlimited). Public is **not** required for it to be free — it matters for the portfolio.
- OpenF1 is free; BigQuery holds ~10.7 MB against 10 GB free, and queries stay far under the
  1 TB/month free tier.
- Once on GitHub the cron runs on GitHub's runners — the Mac does not need to be on.
- dbt Cloud: set aside for now, worth revisiting later.
