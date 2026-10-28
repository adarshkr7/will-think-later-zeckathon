"""PRAHARI offline desk. Reads exported outputs only; never fits or scores."""

import os

import pandas as pd
import streamlit as st

from prahari.data.output_store import OutputStore


st.set_page_config(page_title="PRAHARI · Credit review", page_icon="◉", layout="wide")


@st.cache_resource
def store(path: str) -> OutputStore:
    return OutputStore(path)


@st.cache_data
def frame(path: str, key: str) -> pd.DataFrame:
    return OutputStore(path).frame(key)


def main() -> None:
    path = os.environ.get("PRAHARI_APP_MANIFEST")
    if not path:
        st.error("Start the app with run_app.ps1 so it receives the configured output bundle.")
        return
    output = store(path)
    manifest = output.manifest
    settings = manifest["settings"]
    palette = settings["palette"]
    st.markdown(f"""<style>
      .stApp {{background:{palette['background']};}}
      .block-container {{padding-top:1.4rem;max-width:1500px;}}
      [data-testid="stMetric"] {{background:white;border:1px solid #e1e7ef;border-radius:12px;padding:15px 20px;}}
      [data-testid="stMetricValue"] {{color:{palette['navy']};}}
      .desk-banner {{background:{palette['navy']};color:white;border-radius:16px;padding:24px 30px;margin-bottom:20px;}}
      .desk-banner h1 {{color:white;font-size:2.2rem;letter-spacing:.12em;padding:0;}}
      .desk-banner p {{color:#c1d6df;margin:4px 0 0;}}
      .small-label {{text-transform:uppercase;letter-spacing:.14em;font-size:.7rem;color:#8eafb9;}}
      [data-testid="stTabs"] button {{font-weight:600;}}
    </style>
    <div class="desk-banner"><div class="small-label">Evidence before escalation</div>
    <h1>◉ PRAHARI</h1><p>Point-in-time credit review desk · cached evidence · offline</p></div>""", unsafe_allow_html=True)
    if manifest["mode"] == "readiness_only":
        st.warning("Readiness view: verified inputs are available; scored Indian replay remains gated. Blank probabilities and ranks are intentional.")
    else:
        st.success("Registered replay. All displayed scores and explanations were computed offline.")
    columns = st.columns(len(manifest["kpis"]))
    for column, item in zip(columns, manifest["kpis"], strict=True):
        column.metric(item["label"], item["value"] if item["value"] is not None else "Unavailable")
    snapshots = frame(path, "app_snapshots")
    if snapshots.empty:
        st.info("Build the offline bundle before opening historical snapshots.")
        return
    quarters = manifest["quarters"]
    default = settings["demo_quarter"] if settings["demo_quarter"] in quarters else quarters[-1]
    with st.sidebar:
        st.subheader("Review context")
        arena = st.selectbox("Arena", manifest["arenas"], format_func=lambda value: "Matched panel" if value == "P" else "Background universe")
        quarter = st.select_slider("Scoring cutoff", options=quarters, value=default)
        st.caption("Only documents public before the selected cutoff enter features. Company names may be retrospective catalog labels.")
        st.divider()
        st.subheader("Judge's pick")
        query = st.text_input("ISIN, symbol or company", placeholder="Search the cached universe")
        if st.button("Refresh exported files"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    selected = snapshots.loc[snapshots.arena.eq(arena) & snapshots.quarter.eq(quarter)]
    if query.strip():
        search = snapshots[["entity_id", "name", "symbols"]].fillna("").astype(str)
        matches = search.apply(lambda column: column.str.contains(query.strip(), case=False, regex=False)).any(axis=1)
        options = snapshots.loc[matches, "entity_id"].drop_duplicates().tolist()
    else:
        options = selected.entity_id.drop_duplicates().tolist()
    if not options:
        st.info("This firm or quarter is not in the exported cache. No live computation is performed.")
        return
    catalog = snapshots.drop_duplicates("entity_id").set_index("entity_id")
    def borrower_label(key):
        row = catalog.loc[key]
        return str(row["name"]) if pd.notna(row["name"]) else (str(row["symbols"]) if pd.notna(row["symbols"]) else key)
    entity = st.selectbox("Borrower", options, format_func=borrower_label)
    tabs = st.tabs(["Time Machine", "Case Timeline", "Borrower Memo", "Policy & Metrics"])
    with tabs[0]:
        st.subheader("Historical snapshot")
        st.caption(f"Arena {arena} · {quarter} · probabilities are fractions, not certainty of default")
        if selected.empty:
            st.info("No exported snapshot exists for this arena and quarter.")
        else:
            columns = [name for name in settings["tables"]["snapshot"] if name in selected]
            st.dataframe(selected[columns], hide_index=True, width="stretch", height=390)
        details = frame(path, "app_features")
        borrower = details.loc[details.entity_id.eq(entity) & details.arena.eq(arena) & details.scoring_date.astype(str).str.startswith(quarter)]
        with st.expander("Inspect observed features and missing-input reasons", expanded=False):
            st.dataframe(borrower[[name for name in ["feature", "value", "reason", "max_source_date"] if name in borrower]], hide_index=True, width="stretch")
    with tabs[1]:
        st.subheader("Case timeline")
        history = snapshots.loc[snapshots.entity_id.eq(entity) & snapshots.arena.eq(arena)]
        if history.pd_4q.notna().any():
            figure = {"data": [{"type": "scatter", "mode": "lines", "x": history.quarter.tolist(), "y": history[name].tolist(), "name": name, "connectgaps": False} for name in ("pd_4q", "pd_8q")], "layout": {"yaxis": {"title": "Model probability"}, "xaxis": {"title": "Scoring cutoff"}}}
            st.plotly_chart(figure, width="stretch")
        else:
            st.info("No registered probability path exists for this borrower. The table shows the stored evidence coverage instead.")
            if "observed_close" in history and history.observed_close.notna().any():
                figure = {"data": [{"type": "scatter", "mode": "lines+markers", "x": history.quarter.tolist(), "y": history.observed_close.tolist(), "connectgaps": False, "line": {"color": palette["teal"]}}], "layout": {"yaxis": {"title": "Observed closing price, INR"}, "xaxis": {"title": "Scoring cutoff"}}}
                st.plotly_chart(figure, width="stretch")
                st.caption("Actual cached raw closing prices, not corporate-action-adjusted returns or default probabilities. Missing quarters remain gaps.")
        st.dataframe(history[["quarter", "known_features", "missing_features", "score_status"]], hide_index=True, width="stretch")
        if st.checkbox("Reveal verified outcomes"):
            cases = frame(path, "case_catalog")
            outcome = cases.loc[cases.entity_id.eq(entity)]
            st.dataframe(outcome[[name for name in ["name", "event_date", "public_date", "first_D_rating_date", "cirp_admission_date", "source_urls"] if name in outcome]], hide_index=True, width="stretch")
    with tabs[2]:
        st.subheader("Borrower memo")
        text = output.text("memos", arena, quarter, entity + ".md")
        chosen = selected.loc[selected.entity_id.eq(entity)]
        if not text and not chosen.empty:
            text = chosen.iloc[0].get("memo_markdown", "")
        if text:
            st.markdown(text)
            st.download_button("Download memo", text, file_name=f"{entity}_{quarter}.md", mime="text/markdown")
        else:
            st.info("No memo has been exported for this borrower and quarter.")
    with tabs[3]:
        st.subheader("Protocol and evidence status")
        st.dataframe(frame(path, "run_status"), hide_index=True, width="stretch")
        st.subheader("Policy parameters")
        st.dataframe(frame(path, "app_policy"), hide_index=True, width="stretch")
        st.subheader("Benchmark development results")
        st.caption("Nested outer-fold development results. These are not untouched hold-out estimates; bootstrap intervals condition on fitted predictions.")
        benchmark = frame(path, "benchmark_development_metrics")
        columns = [name for name in settings["tables"]["benchmark"] if name in benchmark]
        st.dataframe(benchmark[columns], hide_index=True, width="stretch")
        if manifest.get("calibration_images"):
            with st.expander("Development calibration plot"):
                picture = st.selectbox("Benchmark reliability plot", manifest["calibration_images"])
                st.image(str(output.path("benchmark_plots", picture)))
        for key, title in [("benchmark_final_metrics", "Final benchmark"), ("india_metrics", "Indian recall with intervals"), ("ablations", "Ablation results"), ("detection_curve", "Detection against ratings"), ("placebo", "Placebo"), ("anti_gaming", "Anti-gaming")]:
            table = frame(path, key)
            if not table.empty:
                st.subheader(title)
                st.dataframe(table, hide_index=True, width="stretch")
        with st.expander("Coverage, sources and amendments"):
            for key in ("panel_acceptance", "collection_status", "coverage_parity", "source_catalog"):
                st.write(key.replace("_", " ").title())
                st.dataframe(frame(path, key), hide_index=True, width="stretch")
            st.text(output.text("amendments") or "No amendment log has been created.")


if __name__ == "__main__":
    main()
