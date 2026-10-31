# thef1lab

A small end-to-end data platform on Formula 1 data, built to demonstrate real
Data Engineering skills (ingestion, modeling, orchestration, testing) on a
100%-free-tier GCP stack.

```
OpenF1 API
    ↓  (Python, ingestion/)
BigQuery raw dataset       (raw_openf1 — full refresh on every run)
    ↓  (dbt-core, dbt/)
BigQuery staging dataset   (typed/cleaned views)
    ↓
BigQuery marts dataset     (dim_* / fact_* tables + dbt tests)
    ↓
Streamlit dashboard        (dashboard/, public app reading the marts)
Looker Studio              (alternative, connects directly to BigQuery)
```

Orchestration: a single GitHub Actions workflow
([.github/workflows/pipeline.yml](.github/workflows/pipeline.yml)) runs daily,
free, no server to maintain.

## Design decisions (and why)

- **Full refresh, not incremental.** One season of OpenF1 data (meetings,
  sessions, drivers, laps, stints, pit stops, race control, weather, results)
  is a few tens of MB — nowhere near the 10 GB free storage tier. Truncating
  and reloading raw tables daily is simpler than tracking incremental state,
  and BigQuery load jobs are free regardless of volume. Incremental models
  are a natural "v2" improvement — see Roadmap below.
- **No raw telemetry (`car_data`, `location`).** These OpenF1 endpoints stream
  car telemetry at ~3.7 Hz per driver — a single race weekend can produce
  millions of rows. Including them would burn through the free tier fast.
  Left out of the MVP on purpose.
- **Current season only**, per project scope. Historical seasons (2023+) can
  be added later by parameterizing `SEASON_YEAR`.

## Repo structure

```
ingestion/         Python client for the OpenF1 API + BigQuery loader
dbt/                dbt-core project (staging views, mart tables, tests, seeds)
dashboard/          Streamlit app reading the marts (championship, race, head-to-head)
.github/workflows/  Scheduled pipeline (GitHub Actions)
```

## 1. GCP setup (one-time, manual)

Project used: **thef1lab**. Everything below stays within BigQuery's
always-free monthly tier (10 GB storage, 1 TB queries) as long as a billing
account is linked — no real cost is expected for this project's data volume,
but set a budget alert anyway (step 4) as a safety net.

### 1.1 Create the BigQuery datasets

In the [BigQuery console](https://console.cloud.google.com/bigquery?project=thef1lab),
create three datasets (all in region **EU**):

- `raw_openf1`
- `staging`
- `marts`

(`dbt` will also create a small `dbt` dataset for seeds/artifacts on first run
— you don't need to create it manually.)

### 1.2 Create a service account for the pipeline

1. Go to [IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts?project=thef1lab)
2. **Create service account** → name it `f1-pipeline`
3. Grant it these two roles (principle of least privilege):
   - `BigQuery Data Editor` (`roles/bigquery.dataEditor`)
   - `BigQuery Job User` (`roles/bigquery.jobUser`)
   - (If you hit permission errors while iterating and want to unblock
     quickly, `BigQuery Admin` is a broader fallback — just switch back to
     the two roles above once things work.)
4. Open the new service account → **Keys** tab → **Add key** → **Create new
   key** → type **JSON** → download it.

Keep this JSON file safe — it's a credential. Never commit it.

### 1.3 Local dev credentials

```bash
mkdir -p credentials
mv ~/Downloads/thef1lab-*.json credentials/thef1lab-service-account.json
cp .env.example .env
# edit .env if needed — defaults already point at credentials/thef1lab-service-account.json
```

### 1.4 GitHub Actions secrets & variables

In your GitHub repo: **Settings → Secrets and variables → Actions**.

Secrets tab — add:
- `GCP_SA_KEY`: paste the **entire contents** of the service account JSON key

Variables tab — add:
- `GCP_PROJECT_ID` = `thef1lab`
- `BQ_RAW_DATASET` = `raw_openf1`
- `BQ_LOCATION` = `EU`

### 1.5 Set a billing budget alert (safety net)

[Billing → Budgets & alerts → Create budget](https://console.cloud.google.com/billing/budgets):
scope it to the `thef1lab` project, set an amount like €5, and keep the
default 50/90/100% email alert thresholds. You should never see a real
charge at this data volume, but this way you'll know immediately if you
ever do.

## 2. Run the pipeline locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Ingest the current season from OpenF1 into BigQuery raw tables
python -m ingestion.run

# 2. Transform: staging views + mart tables + seed + tests
cd dbt
dbt deps
dbt seed
dbt run
dbt test
```

`dbt run`/`dbt test` need a `~/.dbt/profiles.yml` — see
[dbt docs: BigQuery profile setup](https://docs.getdbt.com/reference/warehouse-setups/bigquery-setup)
for the `service-account` method, pointing `keyfile` at
`credentials/thef1lab-service-account.json`.

## 3. Looker Studio (public dashboard)

1. Go to [lookerstudio.google.com](https://lookerstudio.google.com) → **Create → Data source**
2. Choose the **BigQuery** connector → project `thef1lab` → dataset `marts` →
   pick a table (or use **Custom Query** to join `fact_laps`/`fact_race_results`
   with `dim_driver`/`dim_session`)
3. In the data source settings, set **credentials to use → Owner's
   credentials** (not viewer's) — required so that anonymous public viewers
   can see the data without needing their own BigQuery access
4. Build your report, then **Share → Manage access → General access → Anyone
   with the link** to publish it publicly without requiring a Google sign-in
   from viewers

## 4. Streamlit dashboard

`dashboard/` is a Streamlit app with three views: championship (standings,
points progression, constructors), race (lap pace, tyre strategy, fastest
stops) and driver head-to-head. It only reads `marts` tables; every SQL query
lives in `dashboard/queries.py` behind a column contract, so a dbt change
means editing one file.

**Run locally** (from the repo root, reuses your `.env` and service account):

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
# no credentials yet? DEMO_MODE=1 streamlit run dashboard/app.py
```

**Publish for free** on Streamlit Community Cloud:

1. Create a **read-only** service account `f1-dashboard` with
   `BigQuery Data Viewer` + `BigQuery Job User`, and download its JSON key.
   Don't reuse `f1-pipeline`: it can write, and this key leaves GCP.
2. [share.streamlit.io](https://share.streamlit.io) → **New app** → this repo,
   main file `dashboard/app.py`.
3. **Advanced settings → Secrets**: paste `.streamlit/secrets.toml.example`
   filled with the key.

Queries are cached for 1 hour, so BigQuery cost stays at zero in practice.

## Roadmap / nice-to-haves

- Incremental dbt models (`is_incremental()`) once you want to extend beyond
  a single season
- Historical seasons (2023+) by looping `SEASON_YEAR`
- A sampled telemetry mart (one showcase session) if you want to show
  `car_data`/`location` handling without blowing the storage budget
- `dbt docs generate` published to GitHub Pages for a public lineage graph —
  a strong portfolio artifact on its own
