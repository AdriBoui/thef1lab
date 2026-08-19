import json
import logging

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from ingestion.config import BQ_LOCATION, BQ_RAW_DATASET, GCP_PROJECT_ID

logger = logging.getLogger(__name__)


def _jsonify_nested_fields(rows: list[dict]) -> None:
    """Serialise any nested (list/dict) field value to a JSON string, in place.

    BigQuery's schema autodetection is brittle on nested JSON: it models an
    array as a REPEATED field (which cannot be NULL, only empty), so OpenF1
    fields like laps.segments_sector_1 — returned as an int array on some
    rows and null on others — break the load.

    Landing semi-structured fields as JSON strings is a standard raw-layer
    pattern: the raw table stays a faithful, loadable copy of the source,
    and any consumer that needs the structure can parse it downstream (e.g.
    BigQuery's JSON functions in a dbt model). We don't currently model any
    of these fields, so a string column is all we need."""
    for row in rows:
        for key, value in row.items():
            if isinstance(value, (list, dict)):
                row[key] = json.dumps(value)


def get_client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT_ID)


def ensure_raw_dataset(client: bigquery.Client) -> None:
    dataset_id = f"{GCP_PROJECT_ID}.{BQ_RAW_DATASET}"
    try:
        client.get_dataset(dataset_id)
    except NotFound:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = BQ_LOCATION
        client.create_dataset(dataset)
        logger.info("Created dataset %s in %s", dataset_id, BQ_LOCATION)


def load_rows(client: bigquery.Client, table_name: str, rows: list[dict]) -> None:
    """Full refresh load: truncates and reloads the table.

    Safe and cheap for this project's data volume (one season of OpenF1
    data comfortably fits the BigQuery always-free storage tier), and
    much simpler than tracking incremental state across daily runs.
    """
    if not rows:
        logger.warning("No rows to load for %s, skipping", table_name)
        return

    _jsonify_nested_fields(rows)

    table_id = f"{GCP_PROJECT_ID}.{BQ_RAW_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    job.result()
    logger.info("Loaded %d rows into %s", len(rows), table_id)
