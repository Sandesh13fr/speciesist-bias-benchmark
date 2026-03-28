"""Model detail page rendering."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render_model_detail(df: pd.DataFrame) -> None:
    """Render detailed analytics for a selected model.

    Args:
        df: Filtered run DataFrame.
    """
    st.subheader("Model Detail")
    if df.empty:
        st.info("No records available for selected filters.")
        return

    model_ids = sorted([value for value in df["model_id"].dropna().unique().tolist() if str(value).strip()])
    if not model_ids:
        st.info("No model identifiers available in this filtered dataset.")
        return

    selected_model = st.selectbox("Select model", options=model_ids)
    model_df = df[df["model_id"] == selected_model].copy()

    completed_count = int((model_df["response_status"] == "completed").sum())
    failure_count = int((model_df["response_status"] != "completed").sum())
    avg_score = float(model_df["normalized_score"].dropna().mean()) if model_df["normalized_score"].notna().any() else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Completed", completed_count)
    col2.metric("Failures", failure_count)
    col3.metric("Avg Score", f"{avg_score:.2f}")

    st.markdown("### Per-Dimension Score Breakdown")
    dim_df = (
        model_df[model_df["normalized_score"].notna()]
        .groupby("dimension", dropna=True)["normalized_score"]
        .mean()
        .reset_index()
        .sort_values("normalized_score", ascending=False)
    )
    if dim_df.empty:
        st.caption("No scored records for selected model under current filters.")
    else:
        figure = px.bar(
            dim_df,
            x="dimension",
            y="normalized_score",
            labels={"dimension": "Dimension", "normalized_score": "Average Score"},
            title="Average Score by Dimension",
        )
        figure.update_layout(yaxis_range=[0, 10])
        st.plotly_chart(figure, use_container_width=True)

    st.markdown("### Prompt-Level Table")
    prompt_table = model_df[
        [
            "case_id",
            "dimension",
            "response_status",
            "normalized_score",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "rationale",
        ]
    ].copy()
    prompt_table = prompt_table.rename(columns={"response_status": "status"})
    st.dataframe(prompt_table, use_container_width=True, hide_index=True)

    st.markdown("### Raw Response Excerpts")
    excerpts = model_df[["case_id", "dimension", "response_text"]].copy()
    excerpts["response_excerpt"] = excerpts["response_text"].fillna("").astype(str).str.slice(0, 280)
    excerpts = excerpts.drop(columns=["response_text"])
    st.dataframe(excerpts, use_container_width=True, hide_index=True)

    st.markdown("### Failure Diagnostics")
    failures = model_df[model_df["response_status"] != "completed"][
        ["case_id", "dimension", "response_status", "error_message", "latency_ms"]
    ].copy()
    failures = failures.rename(columns={"response_status": "status"})
    if failures.empty:
        st.success("No failures for selected model under current filters.")
    else:
        st.dataframe(failures, use_container_width=True, hide_index=True)
