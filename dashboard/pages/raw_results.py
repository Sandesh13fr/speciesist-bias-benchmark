"""Raw results page rendering."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from dashboard.components import render_raw_response_viewer


def render_raw_results(df: pd.DataFrame) -> None:
    """Render searchable and filterable raw benchmark results.

    Args:
        df: Filtered run DataFrame.
    """
    st.subheader("Raw Results")
    if df.empty:
        st.info("No records available for selected filters.")
        return

    query = st.text_input("Search prompt/response/error text", value="").strip().lower()
    if query:
        mask = (
            df["prompt_text"].fillna("").astype(str).str.lower().str.contains(query, na=False)
            | df["response_text"].fillna("").astype(str).str.lower().str.contains(query, na=False)
            | df["error_message"].fillna("").astype(str).str.lower().str.contains(query, na=False)
            | df["case_id"].fillna("").astype(str).str.lower().str.contains(query, na=False)
            | df["model_id"].fillna("").astype(str).str.lower().str.contains(query, na=False)
        )
        filtered = df[mask].copy()
    else:
        filtered = df.copy()

    st.caption(f"Rows shown: {len(filtered)}")
    display_columns = [
        "response_id",
        "model_id",
        "dimension",
        "case_id",
        "response_status",
        "normalized_score",
        "latency_ms",
        "error_message",
        "response_created_at",
    ]
    table = filtered[display_columns].rename(columns={"response_status": "status"})
    st.dataframe(table, use_container_width=True, hide_index=True)

    render_raw_response_viewer(filtered)

    st.markdown("### Score Breakdown JSON Preview")
    preview_df = filtered[["response_id", "model_id", "dimension", "breakdown_json"]].copy()
    preview_df = preview_df[preview_df["breakdown_json"].notna()]

    if preview_df.empty:
        st.caption("No score breakdown JSON available for selected rows.")
        return

    options = [
        f"response_id={int(row.response_id)} | {row.model_id} | {row.dimension}"
        for row in preview_df.itertuples(index=False)
    ]
    selected_option = st.selectbox("Choose breakdown row", options=options)
    selected_index = options.index(selected_option)
    payload = str(preview_df.iloc[selected_index]["breakdown_json"])

    with st.expander("View breakdown JSON", expanded=True):
        try:
            st.json(json.loads(payload))
        except json.JSONDecodeError:
            st.code(payload, language="json")
