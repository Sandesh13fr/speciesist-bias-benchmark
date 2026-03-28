"""Streamlit read-only dashboard entrypoint."""

from __future__ import annotations

import logging
import webbrowser
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from config import load_settings
from dashboard.components import load_run_dataframe
from dashboard.pages.model_detail import render_model_detail
from dashboard.pages.overview import render_overview
from dashboard.pages.raw_results import render_raw_results
from logging_config import configure_logging

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_available_runs(database_url: str) -> pd.DataFrame:
    """Load available benchmark runs from SQLite.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        DataFrame of available runs ordered by most recent first.
    """
    query = text(
        """
        SELECT
            id,
            run_label,
            status,
            benchmark_version,
            started_at,
            completed_at,
            selected_models_json,
            selected_dimensions_json,
            notes
        FROM runs
        ORDER BY started_at DESC, id DESC
        """
    )
    engine = create_engine(database_url, future=True)
    with engine.connect() as connection:
        return pd.read_sql_query(query, connection)


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters to selected run data.

    Args:
        df: Run DataFrame.

    Returns:
        Filtered DataFrame.
    """
    if df.empty:
        return df

    model_options = sorted([value for value in df["model_id"].dropna().unique().tolist() if str(value).strip()])
    default_models = model_options
    selected_models = st.sidebar.multiselect("Model filter", options=model_options, default=default_models)

    dimension_options = sorted(
        [value for value in df["dimension"].dropna().unique().tolist() if str(value).strip()]
    )
    default_dimensions = dimension_options
    selected_dimensions = st.sidebar.multiselect(
        "Dimension filter",
        options=dimension_options,
        default=default_dimensions,
    )

    scored = df["normalized_score"].dropna()
    min_score = float(scored.min()) if not scored.empty else 0.0
    max_score = float(scored.max()) if not scored.empty else 10.0
    if min_score > max_score:
        min_score, max_score = 0.0, 10.0
    score_range = st.sidebar.slider(
        "Score range",
        min_value=float(min_score),
        max_value=float(max_score),
        value=(float(min_score), float(max_score)),
    )

    show_failures_only = st.sidebar.checkbox("Show failures only", value=False)

    filtered = df.copy()
    if selected_models:
        filtered = filtered[filtered["model_id"].isin(selected_models)]
    if selected_dimensions:
        filtered = filtered[filtered["dimension"].isin(selected_dimensions)]

    low, high = score_range
    within_range = filtered["normalized_score"].between(low, high) | filtered["normalized_score"].isna()
    filtered = filtered[within_range]

    if show_failures_only:
        filtered = filtered[filtered["response_status"] != "completed"]

    return filtered


def _get_selected_run_metadata(runs_df: pd.DataFrame, run_id: int) -> dict[str, Any]:
    row = runs_df[runs_df["id"] == run_id]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def list_report_files(reports_dir: str) -> list[str]:
    """List generated HTML reports ordered by most recent first.

    Args:
        reports_dir: Reports directory path.

    Returns:
        List of absolute report file paths as strings.
    """
    report_paths = sorted(
        Path(reports_dir).glob("*.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [str(path.resolve()) for path in report_paths]


def _open_report_in_new_tab(path: str) -> None:
    """Open report file in a new browser tab.

    Args:
        path: Absolute report file path.
    """
    report_path = Path(path)
    if not report_path.exists():
        st.sidebar.error(f"Report not found: {report_path}")
        return

    webbrowser.open_new_tab(report_path.as_uri())
    st.sidebar.success(f"Opened {report_path.name} in a new tab.")


def main() -> None:
    """Render Streamlit dashboard in read-only mode."""
    settings = load_settings(require_api_key=False)
    configure_logging(settings.log_level)

    st.set_page_config(page_title="Speciesist Bias Benchmark Dashboard", layout="wide")
    st.title("Speciesist Bias Benchmark Dashboard")
    st.caption("Read-only analytics over SQLite benchmark data. This dashboard never calls OpenRouter.")

    runs_df = load_available_runs(settings.database_url)
    if runs_df.empty:
        st.warning("No benchmark runs found. Execute run_benchmark.py first.")
        return

    st.sidebar.header("Run & Filters")
    run_options = {f"{row.run_label} (id={int(row.id)})": int(row.id) for row in runs_df.itertuples(index=False)}
    selected_run_label = st.sidebar.selectbox("Run selector", options=list(run_options.keys()))
    selected_run_id = run_options[selected_run_label]

    run_df = load_run_dataframe(settings.database_url, selected_run_id)
    filtered_df = apply_sidebar_filters(run_df)
    run_metadata = _get_selected_run_metadata(runs_df, selected_run_id)

    st.sidebar.header("Page")
    page = st.sidebar.radio("Route", options=["Overview", "Model Detail", "Raw Results"])

    st.sidebar.header("Reports")
    report_files = list_report_files(str(settings.reports_dir))
    latest_report = Path(settings.reports_dir) / "latest.html"
    if not latest_report.exists():
        st.sidebar.caption("No latest report found yet.")

    if report_files:
        report_options = {Path(path).name: path for path in report_files}
        selection_placeholder = "Select a report..."
        selected_report_name = st.sidebar.selectbox(
            "Select report",
            options=[selection_placeholder, *list(report_options.keys())],
        )
        selected_report_path = report_options.get(selected_report_name)
        if selected_report_path is None:
            st.sidebar.caption("Please select a report first.")
        else:
            if st.sidebar.button("Launch selected report now"):
                _open_report_in_new_tab(selected_report_path)
    else:
        st.sidebar.caption("No report files available in reports/.")

    if page == "Overview":
        render_overview(filtered_df, run_metadata)
    elif page == "Model Detail":
        render_model_detail(filtered_df)
    else:
        render_raw_results(filtered_df)

    logger.info("Rendered dashboard for run_id=%s page=%s", selected_run_id, page)


if __name__ == "__main__":
    main()
