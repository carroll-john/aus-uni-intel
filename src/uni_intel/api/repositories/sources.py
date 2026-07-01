from __future__ import annotations

import duckdb

from uni_intel.api.repositories.base import rows_to_dicts


def list_sources(conn: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    return rows_to_dicts(
        conn,
        """
        SELECT source_file_id, dataset_id, source_name, source_url,
               file_format, reporting_year, downloaded_at, checksum_sha256,
               row_count, license, publication_date, notes
        FROM source_files
        ORDER BY downloaded_at DESC
        """,
    )


def list_quality_checks(conn: duckdb.DuckDBPyConnection, limit: int) -> list[dict[str, object]]:
    return rows_to_dicts(
        conn,
        """
        SELECT q.run_id, q.source_file_id, s.source_name, q.check_name,
               q.status, q.severity, q.observed_value, q.expected_value,
               q.details, q.created_at
        FROM data_quality_checks q
        LEFT JOIN source_files s ON s.source_file_id = q.source_file_id
        ORDER BY q.created_at DESC
        LIMIT ?
        """,
        [limit],
    )
