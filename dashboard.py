import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from load_data import DB_PATH, POPULATIONS
from pipeline import OUTPUT_DIR, get_responder_frequencies


st.set_page_config(page_title="Immune Cell Analysis", layout="wide")
st.title("Immune Cell Analysis")

if not DB_PATH.exists():
    st.error("Run `make pipeline` before starting the dashboard.")
    st.stop()


@st.cache_data
def load_results():
    with sqlite3.connect(DB_PATH) as connection:
        responder_frequencies = get_responder_frequencies(connection)
    return {
        "frequencies": pd.read_csv(OUTPUT_DIR / "sample_frequencies.csv"),
        "response_frequencies": responder_frequencies,
        "statistics": pd.read_csv(OUTPUT_DIR / "responder_statistics.csv"),
        "baseline": pd.read_csv(OUTPUT_DIR / "baseline_samples.csv"),
        "projects": pd.read_csv(OUTPUT_DIR / "samples_by_project.csv"),
        "responses": pd.read_csv(OUTPUT_DIR / "subjects_by_response.csv"),
        "genders": pd.read_csv(OUTPUT_DIR / "subjects_by_gender.csv"),
    }


data = load_results()
overview_tab, response_tab, baseline_tab = st.tabs(
    ["Cell frequencies", "Response analysis", "Baseline subset"]
)

with overview_tab:
    selected_populations = st.multiselect(
        "Populations", POPULATIONS, default=list(POPULATIONS)
    )
    sample_search = st.text_input("Sample contains")
    table = data["frequencies"][
        data["frequencies"]["population"].isin(selected_populations)
    ]
    if sample_search:
        table = table[table["sample"].str.contains(sample_search, case=False)]
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button(
        "Download table",
        table.to_csv(index=False),
        "sample_frequencies.csv",
        "text/csv",
    )

with response_tab:
    st.caption(
        "Melanoma samples receiving miraclib, PBMC only. Each observation is one sample."
    )
    plot_data = data["response_frequencies"]
    figure = px.box(
        plot_data,
        x="response",
        y="percentage",
        color="response",
        facet_col="population",
        facet_col_wrap=3,
        points=False,
        labels={"percentage": "Relative frequency per sample (%)"},
    )
    figure.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    figure.update_layout(showlegend=False)
    st.plotly_chart(figure, width="stretch")
    st.subheader("Mann–Whitney U results")
    st.dataframe(data["statistics"], hide_index=True, width="stretch")
    significant = data["statistics"].loc[
        data["statistics"]["significant"], "population"
    ]
    adjusted_significant = data["statistics"].loc[
        data["statistics"]["significant_after_bh"], "population"
    ]
    st.write(
        "Nominal p < 0.05: "
        + (", ".join(significant) or "none")
    )
    st.write(
        "Significant after Benjamini–Hochberg correction: "
        + (", ".join(adjusted_significant) or "none")
    )

with baseline_tab:
    st.caption("Melanoma PBMC samples treated with miraclib at day 0")
    left, middle, right = st.columns(3)
    left.subheader("Samples by project")
    left.dataframe(data["projects"], hide_index=True, width="stretch")
    middle.subheader("Subjects by response")
    middle.dataframe(data["responses"], hide_index=True, width="stretch")
    right.subheader("Subjects by gender")
    right.dataframe(data["genders"], hide_index=True, width="stretch")

    projects = sorted(data["baseline"]["project"].unique())
    selected_projects = st.multiselect("Projects", projects, default=projects)
    baseline = data["baseline"][data["baseline"]["project"].isin(selected_projects)]
    st.dataframe(baseline, hide_index=True, width="stretch")
