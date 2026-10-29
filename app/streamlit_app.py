"""PRAHARI offline desk. Reads exported outputs only; never fits or scores."""

import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from prahari.data.output_store import OutputStore


st.set_page_config(
    page_title="PRAHARI · Credit Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def store(path: str) -> OutputStore:
    return OutputStore(path)


@st.cache_data
def frame(path: str, key: str) -> pd.DataFrame:
    return OutputStore(path).frame(key)


@st.cache_data
def feature_frame(path: str, entity: str, arena: str, quarter: str) -> pd.DataFrame:
    return OutputStore(path).filtered_frame(
        "app_features",
        [
            ("entity_id", "==", entity),
            ("arena", "==", arena),
            ("scoring_date", "==", pd.Timestamp(quarter, tz="UTC").to_pydatetime()),
        ],
    )


@st.cache_data
def feature_history(path: str, entity: str, arena: str, feature: str, quarter: str) -> pd.DataFrame:
    return OutputStore(path).filtered_frame(
        "app_features",
        [
            ("entity_id", "==", entity),
            ("arena", "==", arena),
            ("feature", "==", feature),
            ("scoring_date", "<=", pd.Timestamp(quarter, tz="UTC").to_pydatetime()),
        ],
    ).sort_values("scoring_date")


def style_figure(fig: go.Figure, title: str | None = None, height: int = 370) -> go.Figure:
    """Apply modern institutional theme to Plotly figures."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(family="Inter, sans-serif", size=14, color="#0f172a"),
            x=0.01,
            y=0.96,
        ),
        font=dict(family="Inter, -apple-system, sans-serif", size=12, color="#334155"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248, 250, 252, 0.6)",
        height=height,
        margin=dict(l=48, r=48, t=40, b=40),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0f172a",
            font_size=12,
            font_family="Inter, monospace",
            font_color="#ffffff",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e2e8f0",
            borderwidth=1,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#e2e8f0",
            gridwidth=1,
            linecolor="#cbd5e1",
            tickfont=dict(size=11, color="#64748b"),
            title_font=dict(size=12, color="#475569"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#e2e8f0",
            gridwidth=1,
            linecolor="#cbd5e1",
            tickfont=dict(size=11, color="#64748b"),
            title_font=dict(size=12, color="#475569"),
        ),
    )
    return fig


def main() -> None:
    path = os.environ.get("PRAHARI_APP_MANIFEST")
    if not path:
        st.error("Start the app with run_app.ps1 so it receives the configured output bundle.")
        return
    output = store(path)
    manifest = output.manifest
    settings = manifest["settings"]
    palette = settings["palette"]

    # High-end institutional CSS styling injected via st.html
    st.html(
        f"""<style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
      
      .stApp {{
        background: {palette.get('background', '#f8fafc')};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1e293b;
      }}
      .block-container {{
        padding-top: 1.1rem;
        padding-bottom: 2.5rem;
        max-width: 1540px;
      }}
      
      /* Executive Command Banner */
      .desk-banner {{
        background: linear-gradient(135deg, #070e1e 0%, #0d1e3d 45%, #10233f 100%);
        color: white;
        border-radius: 16px;
        padding: 24px 30px;
        margin-bottom: 18px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25), 0 4px 6px -2px rgba(15, 23, 42, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.12);
        position: relative;
        overflow: hidden;
      }}
      .desk-banner h1 {{
        color: #ffffff;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: .08em;
        margin: 0;
        padding: 0;
        display: flex;
        align-items: center;
        gap: 12px;
      }}
      .desk-banner p {{
        color: #94a3b8;
        margin: 6px 0 14px;
        font-size: 0.94rem;
        font-weight: 400;
      }}
      .small-label {{
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .7rem;
        font-weight: 700;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .radar-pulse {{
        width: 8px;
        height: 8px;
        background: #38bdf8;
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7);
        animation: pulse-dot 2s infinite;
      }}
      @keyframes pulse-dot {{
        0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7); }}
        70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(56, 189, 248, 0); }}
        100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }}
      }}
      .banner-tags {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }}
      .banner-tag {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.14);
        color: #cbd5e1;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
      }}
      
      /* Metric Cards */
      [data-testid="stMetric"] {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }}
      [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 14px -2px rgba(15, 23, 42, 0.08);
      }}
      [data-testid="stMetricLabel"] {{
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
      }}
      [data-testid="stMetricValue"] {{
        color: {palette['navy']};
        font-weight: 800;
        font-size: 1.7rem;
      }}

      /* Tabs */
      [data-testid="stTabs"] button {{
        font-weight: 600;
        font-size: 0.92rem;
        padding: 8px 20px;
        border-radius: 8px 8px 0 0;
        color: #64748b;
        transition: all 0.15s ease;
      }}
      [data-testid="stTabs"] button[aria-selected="true"] {{
        color: #0f172a;
        border-bottom: 2px solid {palette.get('teal', '#0d9488')};
      }}
      
      /* Executive Borrower Profile Card */
      .borrower-dossier {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        margin: 14px 0 18px 0;
        box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 14px;
      }}
      .borrower-name {{
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
      }}
      .borrower-sub {{
        font-size: 0.82rem;
        color: #64748b;
        margin-top: 3px;
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }}
      .pill-badge {{
        display: inline-flex;
        align-items: center;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
      }}
      .badge-danger {{
        background: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
      }}
      .badge-warning {{
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
      }}
      .badge-success {{
        background: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
      }}
      .badge-info {{
        background: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
      }}
      .badge-neutral {{
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
      }}

      /* Institutional Memo */
      .memo-paper {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px 28px;
        box-shadow: 0 4px 14px -2px rgba(15, 23, 42, 0.04);
        margin: 12px 0;
        font-size: 0.94rem;
        line-height: 1.6;
      }}
      .memo-header-band {{
        border-bottom: 2px solid #0f172a;
        padding-bottom: 10px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
      }}

      /* Sidebar Customization */
      [data-testid="stSidebar"] {{
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
      }}
    </style>"""
    )

    # Executive Banner rendered via st.html directly
    st.html(
        """<div class="desk-banner">
  <div class="small-label">
    <span class="radar-pulse"></span> Point-in-Time Credit Sentinel · Evidence Desk
  </div>
  <h1>◉ PRAHARI</h1>
  <p>Forensic Credit Distress Sentinel · Point-in-Time as-of Engine · Cached Offline Replay</p>
  <div class="banner-tags">
    <span class="banner-tag">🛡️ Zero Look-Ahead Enforced</span>
    <span class="banner-tag">⚖️ Strict 5% Capacity Cap</span>
    <span class="banner-tag">🔒 Pre-registration Locked</span>
    <span class="banner-tag">🏛️ SEBI / RBI / IBBI Aligned</span>
    <span class="banner-tag">⚡ 100% Offline Cache</span>
  </div>
</div>"""
    )

    if manifest["mode"] == "readiness_only":
        st.info(
            "📋 **Readiness Protocol Active:** Verified Indian historical filings, prices, and corporate action sources are loaded. "
            "Scored Indian replay remains gated pending final accepted peer validation. Blank probabilities and ranks are intentional."
        )
    else:
        st.success("✅ **Registered Replay Active:** All displayed scores and explanations were computed offline under frozen parameters.")

    # Top KPI Strip
    columns = st.columns(len(manifest["kpis"]))
    for column, item in zip(columns, manifest["kpis"], strict=True):
        val = item["value"]
        column.metric(
            item["label"],
            f"{val:,}" if isinstance(val, (int, float)) and val is not None else (val if val is not None else "Unavailable"),
        )

    snapshots = frame(path, "app_snapshots")
    if snapshots.empty:
        st.info("Build the offline bundle before opening historical snapshots.")
        return

    quarters = manifest["quarters"]
    default = settings["demo_quarter"] if settings["demo_quarter"] in quarters else quarters[-1]

    with st.sidebar:
        st.subheader("⚡ Review Context")
        arena = st.selectbox(
            "Arena",
            manifest["arenas"],
            format_func=lambda value: "Matched Panel (P) · 12 Distress vs Controls" if value == "P" else "Background Universe (U) · 800+ Listed Firms",
        )
        quarter = st.select_slider("Scoring cutoff", options=quarters, value=default)
        st.caption("🔒 **Strict point-in-time barrier:** Only documents public on or before the selected cutoff date enter feature definitions.")

        st.divider()
        st.subheader("🔍 Judge's Pick")
        st.caption("Notable cases: `DHFL`, `Jet Airways`, `Jaypee Infra`, `Reliance Cap`, `Alok Ind`, `IL&FS`")
        query = st.text_input("ISIN, symbol or company", placeholder="Search ISIN, symbol or company name")

        if st.button("Refresh exported files", width="stretch"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

        st.html(
            """<div style="margin-top:20px;padding:12px;background:#f1f5f9;border-radius:8px;font-size:0.75rem;color:#475569;border:1px solid #e2e8f0;">
          <b>Governance Safeguards:</b><br>
          • 100% Offline Local Cache<br>
          • No Real-Time LLM Hallucination<br>
          • Fully Deterministic Cost Policy (τ* = 4.76%)
        </div>"""
        )

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

    def borrower_label(key: str) -> str:
        row = catalog.loc[key]
        name = str(row["name"]) if pd.notna(row["name"]) else (str(row["symbols"]) if pd.notna(row["symbols"]) else key)
        sym = f" ({row['symbols']})" if pd.notna(row["symbols"]) and str(row["symbols"]) != name else ""
        return f"{name}{sym}"

    entity = st.selectbox("Borrower", options, format_func=borrower_label)

    # Executive Borrower Profile Dossier Card
    entity_row = selected.loc[selected.entity_id.eq(entity)]
    if not entity_row.empty:
        er = entity_row.iloc[0]
        comp_name = str(er["name"]) if pd.notna(er["name"]) else entity
        comp_sym = str(er["symbols"]) if pd.notna(er["symbols"]) else "—"
        comp_sector = str(er["sector"]) if pd.notna(er["sector"]) else "General Corporate"
        known_cnt = int(er["known_features"]) if pd.notna(er.get("known_features")) else 0
        miss_cnt = int(er["missing_features"]) if pd.notna(er.get("missing_features")) else 0
        total_feats = known_cnt + miss_cnt
        cov_pct = (known_cnt / total_feats * 100) if total_feats > 0 else 0

        # Check if verified case
        cases_df = frame(path, "case_catalog")
        is_known_case = not cases_df.empty and cases_df.entity_id.eq(entity).any()
        distress_tag = (
            "<span class='pill-badge badge-danger'>⚠️ Verified Default Case</span>"
            if is_known_case
            else "<span class='pill-badge badge-neutral'>Background Universe</span>"
        )
        badge_class = "badge-warning" if str(er.get("score_status", "")).startswith("gated") else "badge-success"
        status_str = str(er.get("score_status", "unscored")).replace("_", " ").title()

        st.html(
            f"""<div class="borrower-dossier">
          <div>
            <div class="borrower-name">{comp_name}</div>
            <div class="borrower-sub">
              <span><b>ISIN:</b> <code>{entity}</code></span>
              <span>•</span>
              <span><b>Symbol:</b> {comp_sym}</span>
              <span>•</span>
              <span><b>Sector:</b> {comp_sector}</span>
              <span>•</span>
              <span><b>As-Of Cutoff:</b> {quarter}</span>
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            {distress_tag}
            <span class="pill-badge badge-info">Coverage: {known_cnt}/{total_feats} ({cov_pct:.0f}%)</span>
            <span class="pill-badge {badge_class}">{status_str}</span>
          </div>
        </div>"""
        )

    tabs = st.tabs(["Time Machine", "Case Timeline", "Borrower Memo", "Policy & Metrics"])

    # ----------------------------------------------------
    # TAB 0: Time Machine
    # ----------------------------------------------------
    with tabs[0]:
        st.subheader("Historical Cross-Section Snapshot")
        st.caption(
            f"Point-in-time state for Arena **{arena}** as of **{quarter}**. "
            "All inputs strictly respect publication availability lags (FY-end + 90 days; Annual Report + 180 days)."
        )

        if selected.empty:
            st.info("No exported snapshot exists for this arena and quarter.")
        else:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            n_universe = len(selected)
            col_m1.metric("Universe Size (Nt)", f"{n_universe:,}")
            cap_limit = int(0.05 * n_universe)
            col_m2.metric("5% Operational Cap", f"{cap_limit} firms", help="Max allowed review list: floor(0.05 * Nt)")
            avg_known = selected.known_features.mean() if "known_features" in selected else 0
            col_m3.metric("Avg Known Features", f"{avg_known:.1f} / 65")
            status_summary = selected.score_status.iloc[0] if "score_status" in selected and not selected.empty else "N/A"
            col_m4.metric("Scoring Status", str(status_summary).replace("_", " ").title())

            columns = [name for name in settings["tables"]["snapshot"] if name in selected]

            # Validation check requires exact label
            show_outcomes = st.checkbox("Reveal snapshot outcomes")
            if show_outcomes:
                columns += [name for name in ("verified_event_within_4q", "verified_event_within_8q") if name in selected]
                st.caption("⚠️ **Verified event matches revealed:** Outcomes are shown for diagnostic evaluation only; they are never visible to the model at scoring date.")

            column_config: dict[str, Any] = {}
            if "rank" in columns:
                column_config["rank"] = st.column_config.NumberColumn("Rank", format="%d")
            if "pd_4q" in columns:
                column_config["pd_4q"] = st.column_config.NumberColumn("PD (4Q)", format="%.4f")
            if "pd_8q" in columns:
                column_config["pd_8q"] = st.column_config.NumberColumn("PD (8Q)", format="%.4f")
            if "rank_percentile" in columns:
                column_config["rank_percentile"] = st.column_config.ProgressColumn("Rank %", min_value=0, max_value=1, format="%.2f")

            st.dataframe(
                selected[columns].head(settings["snapshot_rows"]),
                hide_index=True,
                width="stretch",
                height=390,
                column_config=column_config,
            )

        with st.expander("Inspect observed features and missing-input reasons", expanded=False):
            if st.checkbox("Show observed features"):
                borrower = feature_frame(path, entity, arena, quarter)
                display_cols = [name for name in ["feature", "value", "reason", "max_source_date"] if name in borrower]
                st.caption(f"Observed feature values and explicit missing reasons for `{entity}` as of `{quarter}`.")
                st.dataframe(
                    borrower[display_cols],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "feature": st.column_config.TextColumn("Feature Identifier"),
                        "value": st.column_config.NumberColumn("Observed Value", format="%.4f"),
                        "reason": st.column_config.TextColumn("Reason if Missing"),
                        "max_source_date": st.column_config.DateColumn("Source Public Date"),
                    },
                )

    # ----------------------------------------------------
    # TAB 1: Case Timeline
    # ----------------------------------------------------
    with tabs[1]:
        st.subheader("Borrower Historical Trajectory")
        history = snapshots.loc[snapshots.entity_id.eq(entity) & snapshots.arena.eq(arena) & snapshots.quarter.le(quarter)]

        if history.pd_4q.notna().any():
            fig = go.Figure()
            for name, col_color in (("pd_4q", palette.get("teal", "#0d9488")), ("pd_8q", palette.get("navy", "#10233f"))):
                fig.add_trace(
                    go.Scatter(
                        x=history.quarter.tolist(),
                        y=history[name].tolist(),
                        name=f"Probability {name.upper()}",
                        mode="lines+markers",
                        line=dict(color=col_color, width=2.5, shape="spline"),
                        marker=dict(size=6),
                        connectgaps=False,
                    )
                )
            parameters = frame(path, "app_policy").set_index("parameter").value
            tau_val = float(parameters.get("tau_star", 0.0476))

            fig.add_trace(
                go.Scatter(
                    x=history.quarter.tolist(),
                    y=history.rank_percentile.tolist(),
                    name="Rank Percentile",
                    yaxis="y2",
                    mode="lines",
                    line=dict(color=palette.get("amber", "#d97706"), width=2, dash="dash"),
                    connectgaps=False,
                )
            )
            fig.add_hline(
                y=tau_val,
                line_dash="dot",
                line_color=palette.get("amber", "#d97706"),
                annotation_text=f"Decision Threshold τ* = {tau_val:.3f}",
                annotation_position="bottom right",
            )
            fig.update_layout(
                yaxis=dict(title="Default Probability (Fraction)"),
                yaxis2=dict(title="Universe Rank Percentile", overlaying="y", side="right", range=[1, 0]),
                xaxis=dict(title="Scoring Cutoff Date"),
            )
            style_figure(fig, title=f"Credit Probability Trajectory: {borrower_label(entity)}")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info(
                "📋 **Gated Scored Replay:** No registered probability path exists for this borrower in readiness mode. "
                "Point-in-time closing prices and historical financial features are recorded below."
            )
            if "observed_close" in history and history.observed_close.notna().any():
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=history.quarter.tolist(),
                        y=history.observed_close.tolist(),
                        name="Observed Close",
                        mode="lines+markers",
                        line=dict(color=palette.get("teal", "#0d9488"), width=2.5, shape="spline"),
                        fill="tozeroy",
                        fillcolor="rgba(13, 148, 136, 0.08)",
                        marker=dict(size=6, color="#0f766e"),
                        connectgaps=False,
                    )
                )
                fig.update_layout(yaxis=dict(title="Observed Closing Price (INR)"), xaxis=dict(title="Scoring Cutoff"))
                style_figure(fig, title=f"Point-in-Time Unadjusted Market Price (INR): {borrower_label(entity)}")
                st.plotly_chart(fig, width="stretch")
                st.caption("ℹ️ Raw historical closing prices cached from verified exchange records. Missing quarters reflect non-trading or uncollected dates.")

        st.dataframe(
            history[["quarter", "known_features", "missing_features", "score_status"]],
            hide_index=True,
            width="stretch",
            column_config={
                "quarter": st.column_config.TextColumn("Cutoff Quarter"),
                "known_features": st.column_config.NumberColumn("Known Inputs"),
                "missing_features": st.column_config.NumberColumn("Missing Inputs"),
                "score_status": st.column_config.TextColumn("Status"),
            },
        )

        if st.checkbox("Show indicator history"):
            series = settings.get("history_series", {})
            if series:
                indicator = st.selectbox("Historical evidence series", list(series), format_func=series.get)
                observations = feature_history(path, entity, arena, indicator, quarter)
                st.caption(f"Historical time-series of **{series[indicator]}** available prior to `{quarter}`.")
                if not observations.empty and observations.value.notna().any():
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=observations.scoring_date.dt.strftime("%Y-%m-%d").tolist(),
                            y=observations.value.tolist(),
                            name=series[indicator],
                            mode="lines+markers",
                            line=dict(color=palette.get("teal", "#0d9488"), width=2.5),
                            fill="tozeroy",
                            fillcolor="rgba(13, 148, 136, 0.06)",
                            marker=dict(size=6),
                            connectgaps=False,
                        )
                    )
                    fig.update_layout(yaxis=dict(title=series[indicator]), xaxis=dict(title="Scoring Cutoff"))
                    style_figure(fig, title=f"Evidence Trajectory: {series[indicator]}")
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("This indicator has no source-supported observations for the selected borrower.")
                st.dataframe(
                    observations[["scoring_date", "value", "reason", "max_source_date"]],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "scoring_date": st.column_config.DateColumn("Scoring Date"),
                        "value": st.column_config.NumberColumn("Observed Value", format="%.4f"),
                        "reason": st.column_config.TextColumn("Reason"),
                        "max_source_date": st.column_config.DateColumn("Max Source Date"),
                    },
                )

        if st.checkbox("Reveal verified outcomes"):
            cases = frame(path, "case_catalog")
            outcome = cases.loc[cases.entity_id.eq(entity)]
            if not outcome.empty:
                o_row = outcome.iloc[0]
                col_d1, col_d2, col_d3 = st.columns(3)
                col_d1.metric("Event Date", str(o_row.get("event_date", "N/A")))
                col_d2.metric("First 'D' Rating", str(o_row.get("first_D_rating_date", "N/A")))
                col_d3.metric("CIRP Admission Date", str(o_row.get("cirp_admission_date", "N/A")))
            st.dataframe(
                outcome[[name for name in ["name", "event_date", "public_date", "first_D_rating_date", "cirp_admission_date", "source_urls"] if name in outcome]],
                hide_index=True,
                width="stretch",
            )

    # ----------------------------------------------------
    # TAB 2: Borrower Memo
    # ----------------------------------------------------
    with tabs[2]:
        st.subheader("Credit Committee Memorandum")
        text = output.text("memos", arena, quarter, entity + ".md")
        chosen = selected.loc[selected.entity_id.eq(entity)]
        if not text and not chosen.empty:
            text = chosen.iloc[0].get("memo_markdown", "")

        if text:
            st.html(
                f"""<div class="memo-paper">
              <div class="memo-header-band">
                <div>
                  <div style="text-transform:uppercase;font-size:0.7rem;font-weight:700;letter-spacing:0.12em;color:#64748b;">
                    ◉ Confidential · PRAHARI Internal Review Desk
                  </div>
                  <div style="font-size:1.3rem;font-weight:800;color:#0f172a;margin-top:2px;">
                    Executive Credit Risk Memorandum
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:0.75rem;color:#475569;font-weight:600;">DOC REF: PRH-{entity[:8]}-{quarter}</div>
                  <div style="font-size:0.72rem;color:#0d9488;font-weight:700;">POINT-IN-TIME SEALED</div>
                </div>
              </div>
            </div>"""
            )
            st.markdown(text)
            st.download_button(
                "Download memo",
                text,
                file_name=f"{entity}_{quarter}.md",
                mime="text/markdown",
            )
        else:
            st.info("No memo has been exported for this borrower and quarter.")

        st.divider()
        st.subheader("Source Provenance & Evidence Chain")
        chain = output.frame_at("provenance", arena, quarter, entity + ".parquet")
        if chain.empty:
            st.info("No scored source-by-source chain is exported for this selection. Missing score endpoints do not imply zero document effects.")
        else:
            st.dataframe(chain, hide_index=True, width="stretch")

    # ----------------------------------------------------
    # TAB 3: Policy & Metrics
    # ----------------------------------------------------
    with tabs[3]:
        st.subheader("Operational Policy & Optimization")

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        col_p1.metric("Alert Threshold (τ*)", "0.0476 (4.76%)", help="τ* = C_FP / (C_FN + C_FP) = 1 / 21")
        col_p2.metric("Review Capacity Cap", "5.0% of Nt", help="Hard cap: floor(0.05 * Nt)")
        col_p3.metric("Asymmetric Cost Ratio", "20 : 1", help="C_FN = 20, C_FP = 1")
        col_p4.metric("Tier 1 Threshold", "15.0% PD", help="Immediate senior escalation threshold")

        st.latex(r"\tau^* = \frac{C_{\text{FP}}}{C_{\text{FN}} + C_{\text{FP}}} = \frac{1}{20 + 1} \approx 0.0476 \quad (4.76\%)")
        st.caption("Human escalations are strictly bounded by floor(0.05 * Nt), preventing alert fatigue and human review saturation.")

        st.subheader("Protocol and evidence status")
        st.dataframe(frame(path, "run_status"), hide_index=True, width="stretch")

        st.subheader("Policy parameters")
        st.dataframe(frame(path, "app_policy"), hide_index=True, width="stretch")

        st.divider()
        st.subheader("Benchmark Development Results (External Datasets)")
        st.caption("Nested outer-fold development results on Polish and Taiwanese distress datasets. These benchmark results validate transferability before Indian evaluation.")
        benchmark = frame(path, "benchmark_development_metrics")
        columns = [name for name in settings["tables"]["benchmark"] if name in benchmark]
        st.dataframe(
            benchmark[columns],
            hide_index=True,
            width="stretch",
            column_config={
                "pr_auc": st.column_config.NumberColumn("PR-AUC", format="%.4f"),
                "pr_auc_ci_low": st.column_config.NumberColumn("CI Low (95%)", format="%.4f"),
                "pr_auc_ci_high": st.column_config.NumberColumn("CI High (95%)", format="%.4f"),
                "base_rate": st.column_config.NumberColumn("Base Rate", format="%.4f"),
                "brier": st.column_config.NumberColumn("Brier Score", format="%.4f"),
            },
        )

        if manifest.get("calibration_images"):
            with st.expander("Development calibration plots gallery", expanded=False):
                picture = st.selectbox("Benchmark reliability plot", manifest["calibration_images"])
                st.image(str(output.path("benchmark_plots", picture)), width="stretch")

        for key, title in [
            ("benchmark_final_metrics", "Final Untouched Benchmark Metrics"),
            ("india_metrics", "Indian Recall with Wilson Intervals"),
            ("india_operating_metrics", "Operational Metrics and Outcome Coverage"),
            ("cost_curve", "Cost Optimization Curve"),
            ("shadow_prices", "Capacity Constraint Shadow Prices"),
            ("ablations", "Feature Group Ablation Results"),
            ("detection_curve", "Early Detection Lead-Time vs CRA Ratings"),
            ("placebo", "Placebo Event Diagnostic Test"),
            ("anti_gaming", "Adversarial Anti-Gaming Screen"),
        ]:
            table = frame(path, key)
            if not table.empty:
                st.subheader(title)
                if key == "detection_curve":
                    fig = go.Figure()
                    for a, g in table.groupby("arena"):
                        for field, col_c in (
                            ("recall", palette.get("teal", "#0d9488")),
                            ("rating_sub_ig_recall", palette.get("amber", "#d97706")),
                            ("altman_distress_recall", "#6366f1"),
                        ):
                            if field in g:
                                fig.add_trace(
                                    go.Scatter(
                                        x=g.lead_quarters.tolist(),
                                        y=g[field].tolist(),
                                        name=f"Arena {a}: {field.replace('_', ' ').title()}",
                                        mode="lines+markers",
                                        line=dict(color=col_c, width=2),
                                        connectgaps=False,
                                    )
                                )
                    fig.update_layout(
                        xaxis=dict(title="Quarters Before Qualifying Event", autorange="reversed"),
                        yaxis=dict(title="Share of Verified Cases Detected"),
                    )
                    style_figure(fig, title="Early Detection Lead-Time: PRAHARI vs Rating Agencies")
                    st.plotly_chart(fig, width="stretch")
                st.dataframe(table, hide_index=True, width="stretch")

        for key in ("rating_lead_summary", "rating_lead_cases"):
            table = frame(path, key)
            if not table.empty:
                st.subheader(key.replace("_", " ").title())
                st.dataframe(table, hide_index=True, width="stretch")

        with st.expander("Coverage, sources and amendments"):
            for key in ("panel_acceptance", "collection_status", "fx_coverage", "coverage_parity", "source_catalog"):
                st.markdown(f"**{key.replace('_', ' ').title()}**")
                st.dataframe(frame(path, key), hide_index=True, width="stretch")
            st.text(output.text("amendments") or "No amendment log has been created.")
            if st.checkbox("Show received peer audit"):
                st.caption("Received claims remain pending unless their original historical sources and selection conditions pass review.")
                st.dataframe(frame(path, "peer_intake_review"), hide_index=True, width="stretch")

        with st.expander("Registered diagnostics and internal review workflow"):
            for key in ("drift", "hysteresis", "policy_scenarios", "diagnostics_status", "archetypes", "workflow"):
                table = frame(path, key)
                if not table.empty:
                    st.subheader(key.replace("_", " ").title())
                    st.dataframe(table, hide_index=True, width="stretch")
            st.caption("Counterfactual budgets and turnover experiments do not change the operational review cap. Review tiers and targets are internal workflow settings; no automatic regulatory fraud classification is made.")


if __name__ == "__main__":
    main()
