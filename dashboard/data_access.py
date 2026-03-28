"""Read-only data access for Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text


class ReadOnlyDashboardStore:
    """Read-only query layer for benchmark dashboard.

    Args:
        database_url: SQLAlchemy database URL.
    """

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, future=True)

    def list_runs(self) -> pd.DataFrame:
        """Return benchmark run list.

        Returns:
            DataFrame of benchmark runs sorted by newest first.
        """
        query = text(
            """
            SELECT id, run_uuid, created_at, requested_models, requested_dimensions, status
            FROM benchmark_runs
            ORDER BY created_at DESC
            """
        )
        with self._engine.connect() as connection:
            return pd.read_sql_query(query, connection)

    def load_aggregate_scores(self, run_uuid: str) -> pd.DataFrame:
        """Return per-model aggregated dimension scores for one run.

        Args:
            run_uuid: Public run UUID.

        Returns:
            DataFrame of per-model aggregate scores.
        """
        query = text(
            """
            SELECT
                pr.model_id,
                ROUND(AVG(CASE WHEN pr.dimension = 'euphemism' THEN pr.score END), 2) AS euphemism,
                ROUND(AVG(CASE WHEN pr.dimension = 'food_defaults' THEN pr.score END), 2) AS food_defaults,
                ROUND(AVG(CASE WHEN pr.dimension = 'framing_neutrality' THEN pr.score END), 2) AS framing_neutrality,
                ROUND(AVG(pr.score), 2) AS composite
            FROM prompt_results pr
            JOIN benchmark_runs br ON br.id = pr.run_id
            WHERE br.run_uuid = :run_uuid
            GROUP BY pr.model_id
            ORDER BY composite DESC
            """
        )
        with self._engine.connect() as connection:
            return pd.read_sql_query(query, connection, params={"run_uuid": run_uuid})

    def load_raw_results(self, run_uuid: str) -> pd.DataFrame:
        """Return raw prompt-level records for one run.

        Args:
            run_uuid: Public run UUID.

        Returns:
            DataFrame with prompt-level results.
        """
        query = text(
            """
            SELECT
                pr.model_id,
                pr.dimension,
                pr.prompt_name,
                pr.score,
                pr.rationale,
                pr.prompt_text,
                pr.response_text,
                pr.created_at
            FROM prompt_results pr
            JOIN benchmark_runs br ON br.id = pr.run_id
            WHERE br.run_uuid = :run_uuid
            ORDER BY pr.model_id, pr.dimension, pr.prompt_name
            """
        )
        with self._engine.connect() as connection:
            return pd.read_sql_query(query, connection, params={"run_uuid": run_uuid})
