"""Overview page for benchmark run analytics."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_dimension_bar_chart,
    render_kpi_cards,
    render_model_comparison_table,
)


def render_overview(df: pd.DataFrame, run_metadata: dict[str, Any]) -> None:
    """Render the overview page.

    Args:
        df: Filtered run DataFrame.
        run_metadata: Run metadata dictionary for the selected run.
    """
    st.subheader("Overview")

    render_kpi_cards(df)
    render_model_comparison_table(df)
    render_dimension_bar_chart(df)

    st.subheader("Run Metadata")
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        st.markdown(f"**Run ID:** {run_metadata.get('id', 'N/A')}")
        st.markdown(f"**Run Label:** {run_metadata.get('run_label', 'N/A')}")
        st.markdown(f"**Status:** {run_metadata.get('status', 'N/A')}")
        st.markdown(f"**Benchmark Version:** {run_metadata.get('benchmark_version', 'N/A')}")
    with meta_col2:
        st.markdown(f"**Started At:** {run_metadata.get('started_at', 'N/A')}")
        st.markdown(f"**Completed At:** {run_metadata.get('completed_at', 'N/A')}")
        st.markdown(f"**Selected Models:** {run_metadata.get('selected_models_json', '[]')}")
        st.markdown(f"**Selected Dimensions:** {run_metadata.get('selected_dimensions_json', '[]')}")

    notes = str(run_metadata.get("notes", "") or "").strip()
    if notes:
        st.markdown(f"**Notes:** {notes}")

    st.subheader("How to Interpret Scores")
    st.markdown(
        """
        - Scores are deterministic and rubric-based; higher means stronger speciesist signal.
        - Lower composite scores indicate less detected speciesist bias.
        - Compare models first by composite trend, then inspect per-dimension differences.
        - A high failure count or refusal pattern can indicate reliability risk even with strong scores.
        - Use the Raw Results page to inspect rationale and breakdown JSON before drawing conclusions.
        """
    )
