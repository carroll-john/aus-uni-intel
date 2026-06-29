from __future__ import annotations

import argparse
import json
from pathlib import Path

from uni_intel.config import DB_PATH, FINANCE_URLS
from uni_intel.ingestion.calculations import calculate_metrics
from uni_intel.ingestion.ingest_finance import ingest_finance
from uni_intel.ingestion.ingest_herdc import ingest_herdc
from uni_intel.ingestion.ingest_qilt import ingest_qilt
from uni_intel.ingestion.ingest_student import ingest_student

DATASET_RUNNERS = {
    "student": lambda db_path, force: ingest_student(2024, db_path, force_download=force),
    "herdc": lambda db_path, force: ingest_herdc(db_path, force_download=force),
    "qilt": lambda db_path, force: ingest_qilt(db_path, force_download=force),
    "calculations": lambda db_path, force: calculate_metrics(db_path),
}


def ingest_configured_finance(db_path: Path, force_download: bool) -> dict[str, object]:
    return {
        str(year): ingest_finance(
            year,
            db_path,
            source_url=source_url,
            force_download=force_download,
        )
        for year, source_url in sorted(FINANCE_URLS.items())
    }


def run_all(db_path: Path = DB_PATH, force_download: bool = False) -> dict[str, object]:
    results: dict[str, object] = {
        "finance": ingest_configured_finance(db_path, force_download),
    }
    for name, runner in DATASET_RUNNERS.items():
        results[name] = runner(db_path, force_download)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all configured ingestion pipelines.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(run_all(args.db_path, args.force_download), indent=2))


if __name__ == "__main__":
    main()
