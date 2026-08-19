import os

from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BQ_RAW_DATASET = os.environ.get("BQ_RAW_DATASET", "raw_openf1")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "EU")
SEASON_YEAR = int(os.environ.get("SEASON_YEAR", 0)) or None

OPENF1_BASE_URL = "https://api.openf1.org/v1"
# OpenF1 enforces a hard 30 requests/minute limit. We cap ourselves just
# under it with a sliding-window limiter (see openf1_client) so we never
# trigger a 429 and runs stay predictable (~30 min for a full season).
OPENF1_RATE_LIMIT_PER_MIN = int(os.environ.get("OPENF1_RATE_LIMIT_PER_MIN", "28"))
