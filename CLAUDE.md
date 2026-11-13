# thef1lab — F1 data platform (BigQuery + dbt)

End-to-end data platform on Formula 1 data, built as a Data Engineering portfolio project on a
100%-free-tier GCP stack.

**This is a standalone project.** It is unrelated to `AGI_CDC` and `AGI_API`, which live in
sibling folders under `~/Documents/`. Do not read or edit files outside this directory unless
explicitly asked.

See `README.md` for the full GCP setup and rationale — this file covers only what an agent needs.

## Pipeline

```
OpenF1 API → ingestion/ (Python) → BigQuery raw_openf1 → dbt/ → staging (views) → marts (tables)
                                                                                      ├→ dashboard/ (Streamlit, local)
                                                                                      └→ docs/index.html (page statique, GitHub Pages)
```

Two outputs, one source of SQL: `dashboard/queries.py` (dict `QUERIES` + `CONTRACT`) is read by the
Streamlit app **and** by `dashboard/build_site.py`. Colours live in `dashboard/palette.py`, imported
by `theme.py` and the generator. Never duplicate a query or a hex code between the two.

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
| `dashboard/build_site.py` | Generates `docs/index.html` — hand-written SVG, no charting library |
| `dashboard/palette.py` | Colours shared by the app and the generator (no Plotly import) |
| `docs/` | Served by GitHub Pages: `index.html` (generated) + Looker guide, Notion write-up |
| `.venv/` | Project virtualenv (note the dot — differs from the other two projects) |
| `credentials/` | GCP service-account key — **never commit, never print** |

## Deliberate design choices (don't "fix" these)

- **Full refresh, not incremental** — one season is tens of MB; truncate-and-reload is simpler
  and BigQuery load jobs are free. Incremental is a documented v2, not an oversight.
- **No raw telemetry** (`car_data`, `location`) — ~3.7 Hz per driver would burn the free tier.
- **Current season only** — scope decision; `SEASON_YEAR` is the parameter to change.
- **Tyre degradation is reported RELATIVE to the field**, not absolute. The raw slope is also in
  `fact_stint_degradation`, kept on purpose to show the bias: a car sheds ~1.7 kg per lap, worth
  about 0.05 s, which cancels most of the tyre loss — measured raw, SOFT appears to fade *less*
  than HARD. Do not "simplify" by dropping the relative column.
- **No compound ranking is published.** After correction the spread between compounds (~0.03 to
  ~0.02 s/lap) is the size of the noise; checked that stint length does not drive it (r = −0.06).
  The site shows distributions, not means, for that reason.
- **Safety cars are paired by type** (VSC↔VSC ENDING, SC↔SAFETY CAR IN THIS LAP) and an unmatched
  opening closes after 5 laps. Cross-pairing them marked 27 racing laps as neutralised at Monza
  instead of 8.
- **`track_temperature = 0` is a sentinel**, not a cold track (the raw data has air at 33 °C with
  the track at 0 °C). Nulled out in `fact_lap_conditions`, with everything under 5 °C.
- **Slopes are NULL below 8 clean laps**, and the starting grid comes from OpenF1's
  `starting_grid` endpoint — not the qualifying classification, which penalties make wrong almost
  everywhere.

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
- Commits are authored as `Adrien Bouis <97085201+AdriBoui@users.noreply.github.com>`, set in the
  repo's local config. The repo is public: no real address in the history.
  **`git config user.email` without a scope writes to the shared repo config**, so it changes the
  identity for every worktree. For a throwaway worktree use `git -c user.email=…` on the command
  itself, never `git config`.
- Regenerate the site with `python dashboard/build_site.py` from the repo root (needs `.env`).

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

## Status — 13 November 2026

Steps 1 to 4 of the roadmap are **done**. The repo is `AdriBoui/thef1lab`.

**Seven PRs are stacked and waiting to be merged, in this order.** Each branch contains the
previous ones, so merging out of order recreates conflicts, and **"Squash and merge" / "Rebase and
merge" break the stack** — use "Create a merge commit".

1. `fix/stg-session-result-typing` — `safe_cast` on `position` (OpenF1 returned `'RT'`)
2. `docs/status-steps-1-2`
3. `feat/constructor-standings` — `mart_constructor_standings`, point-in-time teams
4. `feat/grid-vs-result` — `stg_starting_grid`, `fact_grid_vs_result`
5. `feat/tyre-degradation` — `fact_stint_degradation`
6. `feat/weather-conditions` — `fact_lap_conditions`
7. `feat/static-site` — `build_site.py`, `palette.py`, `docs/index.html`

An eighth, `docs/status-static-site`, carries this update.

**History was rewritten on 13 Nov** and force-pushed: all 18 commits now carry the noreply
address, and the merged branch `docs/claude-md-working-mode` was deleted. A scan of every commit
found no secret — the only match was `.streamlit/secrets.toml.example`, which holds `xxx`
placeholders.

### Local setup

- `.env` and `credentials/thef1lab-service-account.json` (`f1-pipeline` key, created 11 Nov; older
  keys revoked). `~/.dbt/profiles.yml` points its `keyfile` there.
- `.venv` on **Python 3.11** via `uv` (matches CI), holding `requirements.txt` +
  `dashboard/requirements.txt`.
- BigQuery `raw_openf1` → `staging` → `marts`, EU, from a full-season ingestion. A full ingestion
  takes **~37 min** (OpenF1 rate limit): run it in the user's Terminal tab, not as a background
  Bash job, which dies when the session ends.
- `dbt build` passes 52/52 on the merged stack.

### Remaining steps

5. **Publish**: merge the seven PRs, make the repo public, then
   *Settings → Pages → Deploy from a branch → `main` / `/docs`*. Streamlit Community Cloud was
   **dropped**: it sleeps, needs a third-party host and a read-only service-account key, and the
   static page needs none of that. The Streamlit app stays for local use and demos.
6. **Re-enable the GitHub Actions cron**, and have the same workflow regenerate `docs/index.html`
   so the site is part of the pipeline rather than a manual step.

The user writes the Notion portfolio themselves, with screenshots, linking to the repo.

### Known open points

- 2 dbt `relationships` warnings: a few `fact_stints` / `fact_pit_stops` driver numbers are missing
  from `dim_driver` (probably reserve drivers) — not investigated.
- `raw_pit` dropped from 6.9k to 1.8k rows between September and November: OpenF1 now returns far
  fewer practice/qualifying pit entries. Race pit stops are consistent.
- Only **2 races** have both wet and dry green-flag laps, and OpenF1's rain flag is binary, so the
  cost-of-rain figure is a small-sample estimate. The site says so.

### Agreed follow-ups (own branch each)

- **Incremental ingestion** by meeting: high watermark read from `raw_meetings` in BigQuery (no
  local state — CI runners are stateless), re-fetch the last meeting as a lookback, delete+insert
  per meeting, keep a `--full-refresh` flag. Cuts a weekly run from ~37 min to ~2 min. This
  replaces the "full refresh" design choice above — update it and the README then.
- **Explicit raw schemas** instead of `autodetect=True` (a first data contract).
- **Workload Identity Federation** for GitHub Actions at step 6, so CI needs no JSON key.
- **A dev dataset per branch** (dbt `target`): BigQuery currently has one shared dev environment,
  so building a model from one branch overwrites another branch's version.

Older notes also live in the user's private Notion workspace — ask them for the link rather than
storing it here: this repo is public, and a Notion page URL is an access path.

### Costs — already verified, no need to recompute

- Weekly cron (~170 min/month at the measured ~37 min/run + dbt): free on a private repo
  (2 000 free minutes/month) and on a public one (unlimited).
- **Public IS required now**, for a different reason: GitHub Pages is free only on public repos.
  It also serves the portfolio.
- Hosting the site costs nothing and needs no credential: the figures are baked into
  `docs/index.html`, so no query is issued when a visitor opens it.
- OpenF1 is free; BigQuery holds ~21 MB of raw data against 10 GB free, and queries stay far under the
  1 TB/month free tier.
- Once on GitHub the cron runs on GitHub's runners — the Mac does not need to be on.
- dbt Cloud: set aside for now, worth revisiting later.
