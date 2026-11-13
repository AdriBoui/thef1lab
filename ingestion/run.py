from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from ingestion.config import SEASON_YEAR
from ingestion.load_to_bigquery import ensure_raw_dataset, get_client, load_rows
from ingestion.openf1_client import OpenF1Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# One entry per raw table: (table_name, client_method_name)
SESSION_LEVEL_ENDPOINTS = [
    ("raw_drivers", "drivers"),
    ("raw_laps", "laps"),
    ("raw_stints", "stints"),
    ("raw_pit", "pit"),
    ("raw_race_control", "race_control"),
    ("raw_weather", "weather"),
    ("raw_session_result", "session_result"),
]

# Only called for qualifying sessions (OpenF1 keys the race grid by them).
QUALIFYING_ENDPOINTS = [
    ("raw_starting_grid", "starting_grid"),
]


def _tag_ingested_at(rows: list[dict], ingested_at: str) -> list[dict]:
    for row in rows:
        row["_ingested_at"] = ingested_at
    return rows


def run(year: int | None = None) -> None:
    year = year or SEASON_YEAR or datetime.now(timezone.utc).year
    ingested_at = datetime.now(timezone.utc).isoformat()

    client = OpenF1Client()
    tables: dict[str, list[dict]] = defaultdict(list)

    logger.info("Fetching meetings for season %s", year)
    meetings = client.meetings(year=year)
    tables["raw_meetings"] = _tag_ingested_at(meetings, ingested_at)

    failures: list[str] = []

    for meeting in meetings:
        meeting_key = meeting["meeting_key"]
        logger.info("Fetching sessions for meeting_key=%s (%s)", meeting_key, meeting.get("meeting_name"))
        try:
            sessions = client.sessions(meeting_key=meeting_key)
        except Exception:
            logger.exception("Failed to fetch sessions for meeting_key=%s, skipping meeting", meeting_key)
            failures.append(f"sessions(meeting_key={meeting_key})")
            continue
        tables["raw_sessions"].extend(_tag_ingested_at(sessions, ingested_at))

        for session in sessions:
            session_key = session["session_key"]
            logger.info(
                "Fetching session-level data for session_key=%s (%s)",
                session_key,
                session.get("session_name"),
            )
            endpoints = SESSION_LEVEL_ENDPOINTS
            if session.get("session_type") == "Qualifying":
                endpoints = SESSION_LEVEL_ENDPOINTS + QUALIFYING_ENDPOINTS
            for table_name, method_name in endpoints:
                try:
                    rows = getattr(client, method_name)(session_key=session_key)
                except Exception:
                    logger.exception(
                        "Failed to fetch %s for session_key=%s, skipping this endpoint for this session",
                        method_name,
                        session_key,
                    )
                    failures.append(f"{method_name}(session_key={session_key})")
                    continue
                tables[table_name].extend(_tag_ingested_at(rows, ingested_at))

    bq_client = get_client()
    ensure_raw_dataset(bq_client)
    for table_name, rows in tables.items():
        load_rows(bq_client, table_name, rows)

    logger.info("Ingestion complete for season %s: %s", year, {k: len(v) for k, v in tables.items()})
    if failures:
        logger.warning("%d endpoint call(s) failed and were skipped: %s", len(failures), failures)


if __name__ == "__main__":
    run()
