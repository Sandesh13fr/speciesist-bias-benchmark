"""Reusable Streamlit components for read-only benchmark analytics."""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text


@st.cache_data(show_spinner=False)
def load_run_dataframe(database_url: str, run_id: int) -> pd.DataFrame:
    """Load run-level benchmark records from SQLite.

    Args:
        database_url: SQLAlchemy database URL.
        run_id: Run identifier in the ``runs`` table.

    Returns:
        Denormalized DataFrame with metadata, response, and score fields.
    """
    query = text(
        """
        SELECT
            r.id AS run_id,
            r.run_label,
            r.status AS run_status,
            r.benchmark_version,
            r.started_at,
            r.completed_at,
            r.selected_models_json,
            r.selected_dimensions_json,
            r.notes,
            p.id AS prompt_id,
            p.case_id,
            p.template_name,
            p.template_checksum,
            p.rendered_prompt,
            p.variables_json,
            resp.id AS response_id,
            COALESCE(resp.model_id, mm.model_id) AS model_id,
            mm.display_name AS model_display_name,
            mm.provider AS model_provider,
            COALESCE(resp.dimension, p.dimension) AS dimension,
            resp.prompt_name,
            resp.prompt_text,
            resp.response_text,
            resp.response_json,
            resp.status AS response_status,
            resp.error_message,
            resp.latency_ms,
            resp.input_tokens,
            resp.output_tokens,
            resp.rationale,
            resp.created_at AS response_created_at,
            s.id AS score_id,
            s.raw_weighted_score,
            s.normalized_score,
            s.scorer_version,
            s.breakdown_json
        FROM runs r
        LEFT JOIN prompts p ON p.run_id = r.id
        LEFT JOIN responses resp ON resp.prompt_id = p.id
        LEFT JOIN scores s ON s.response_id = resp.id
        LEFT JOIN model_metadata mm ON mm.id = resp.model_metadata_id
        WHERE r.id = :run_id
        ORDER BY COALESCE(resp.model_id, mm.model_id), COALESCE(resp.dimension, p.dimension), p.case_id
        """
    )
    engine = create_engine(database_url, future=True)
    with engine.connect() as connection:
        frame = pd.read_sql_query(query, connection, params={"run_id": run_id})

    if frame.empty:
        return frame

    numeric_columns = ["normalized_score", "raw_weighted_score", "latency_ms", "input_tokens", "output_tokens"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame


def render_kpi_cards(df: pd.DataFrame) -> None:
    """Render high-level run KPIs.

    Args:
        df: Filtered benchmark DataFrame for one run.
    """
    if df.empty:
        st.info("No records available for selected filters.")
        return

    total_rows = int(df["response_id"].notna().sum())
    completed_rows = int((df["response_status"] == "completed").sum())
    failed_rows = int((df["response_status"] != "completed").sum())
    avg_score = float(df["normalized_score"].dropna().mean()) if df["normalized_score"].notna().any() else 0.0
    avg_latency = float(df["latency_ms"].dropna().mean()) if df["latency_ms"].notna().any() else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Responses", total_rows)
    col2.metric("Completed", completed_rows)
    col3.metric("Failures", failed_rows)
    col4.metric("Avg Score", f"{avg_score:.2f}")
    col5.metric("Avg Latency (ms)", f"{avg_latency:.0f}")


def render_model_comparison_table(df: pd.DataFrame) -> None:
    """Render model comparison table with per-dimension and composite score columns.

    Args:
        df: Filtered benchmark DataFrame for one run.
    """
    st.subheader("Model Comparison")
    if df.empty:
        st.info("No records available for selected filters.")
        return

    scored = df[df["normalized_score"].notna()].copy()
    if scored.empty:
        st.info("No scored records available for selected filters.")
        return

    pivot = (
        scored.pivot_table(
            index="model_id",
            columns="dimension",
            values="normalized_score",
            aggfunc="mean",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    counts = (
        df.groupby("model_id", dropna=True)
        .agg(
            responses=("response_id", "count"),
            failures=("response_status", lambda s: int((s != "completed").sum())),
        )
        .reset_index()
    )

    table = pivot.merge(counts, on="model_id", how="left")
    score_columns = [col for col in ["euphemism", "food_defaults", "framing_neutrality"] if col in table.columns]
    if score_columns:
        table["composite"] = table[score_columns].mean(axis=1)
    else:
        table["composite"] = 0.0

    display = table.sort_values("composite", ascending=False).copy()
    for column in score_columns + ["composite"]:
        display[column] = display[column].round(2)

    st.dataframe(display, use_container_width=True, hide_index=True)


def render_dimension_bar_chart(df: pd.DataFrame) -> None:
    """Render grouped dimension score chart by model.

    Args:
        df: Filtered benchmark DataFrame for one run.
    """
    st.subheader("Per-Dimension Scores")
    if df.empty:
        st.info("No records available for selected filters.")
        return

    scored = df[df["normalized_score"].notna()].copy()
    if scored.empty:
        st.info("No scored records to chart.")
        return

    grouped = (
        scored.groupby(["model_id", "dimension"], dropna=True)["normalized_score"]
        .mean()
        .reset_index()
    )

    figure = px.bar(
        grouped,
        x="model_id",
        y="normalized_score",
        color="dimension",
        barmode="group",
        labels={"model_id": "Model", "normalized_score": "Avg Score", "dimension": "Dimension"},
        title="Average Dimension Scores by Model",
    )
    figure.update_layout(yaxis_range=[0, 10], legend_title_text="Dimension")
    st.plotly_chart(figure, use_container_width=True)


def render_raw_response_viewer(df: pd.DataFrame) -> None:
    """Render detailed raw response viewer with expandable JSON previews.

    Args:
        df: Filtered benchmark DataFrame for one run.
    """
    st.subheader("Raw Response Viewer")
    if df.empty:
        st.info("No records available for selected filters.")
        return

    rows = df.reset_index(drop=True)
    labels = []
    for idx, row in rows.iterrows():
        labels.append(
            f"{idx + 1}. {row.get('model_id', 'unknown')} | {row.get('dimension', 'n/a')} | "
            f"{row.get('case_id', row.get('prompt_name', 'case'))}"
        )

    selected_label = st.selectbox("Select response", options=labels)
    selected_index = labels.index(selected_label)
    selected_row = rows.iloc[selected_index]

    st.markdown("**Prompt**")
    st.code(str(selected_row.get("prompt_text") or selected_row.get("rendered_prompt") or ""), language="markdown")
    st.markdown("**Response**")
    st.write(str(selected_row.get("response_text") or ""))

    with st.expander("Score Breakdown JSON", expanded=False):
        raw_breakdown = selected_row.get("breakdown_json")
        if isinstance(raw_breakdown, str) and raw_breakdown.strip():
            try:
                st.json(json.loads(raw_breakdown))
            except json.JSONDecodeError:
                st.code(raw_breakdown, language="json")
        else:
            st.caption("No score breakdown available.")

    with st.expander("Raw Response JSON", expanded=False):
        raw_response = selected_row.get("response_json")
        if isinstance(raw_response, str) and raw_response.strip():
            try:
                st.json(json.loads(raw_response))
            except json.JSONDecodeError:
                st.code(raw_response, language="json")
        else:
            st.caption("No raw response JSON stored.")
