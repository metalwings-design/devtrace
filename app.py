"""Streamlit dashboard for DevTrace: Context Switch & Onboarding Hub."""

import os
from pathlib import Path
import sys
from dotenv import load_dotenv
import pandas as pd
import streamlit as st
from supabase import Client, create_client

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

# 1. Page Configuration
st.set_page_config(
    page_title="DevTrace | Engineering Context Switch & Onboarding Hub",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
        st.stop()
    return create_client(url, key)


supabase = get_supabase_client()

st.title("DevTrace")
st.caption("AI-powered Engineering Context Switch Detection & Developer Onboarding Hub")

tab1, tab2, tab3 = st.tabs([
    "Context Switch Timeline",
    "New Hire Project Briefing",
    "Raw Telemetry & Trace",
])

# -------------------------------------------------------------
# TAB 1: Context Switch Timeline
# -------------------------------------------------------------
with tab1:
    st.subheader("Context Switch Timeline")

    try:
        res = (
            supabase.table("context_switches")
            .select("*")
            .order("switched_at", desc=True)
            .execute()
        )
        switches = res.data or []
    except Exception as e:
        st.error(f"Error fetching context switches: {e}")
        switches = []

    if not switches:
        st.info("No context switches detected yet. Run `src/pipeline_runner.py` to ingest and process traces.")
    else:
        df_switches = pd.DataFrame(switches)

        # Metric Bar
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Switches Detected", len(df_switches))
        with col2:
            unique_devs = df_switches["developer_id"].nunique()
            st.metric("Unique Developers Tracked", unique_devs)
        with col3:
            avg_conf = df_switches["confidence_score"].dropna().mean()
            st.metric("Average Confidence", f"{avg_conf * 100:.1f}%" if pd.notnull(avg_conf) else "N/A")

        st.divider()

        # Transitions Display
        for _, row in df_switches.iterrows():
            dev = row.get("developer_id", "Unknown")
            switched_at = row.get("switched_at", "")
            from_proj = row.get("from_project", "")
            to_proj = row.get("to_project", "")
            conf = row.get("confidence_score", 0.0)
            reason = row.get("reason", "No reason provided.")

            with st.container():
                c_title, c_badge = st.columns([4, 1])
                with c_title:
                    st.markdown(
                        f"**`{dev}`** transitioned from **{from_proj}** &rarr; **`{to_proj}`**"
                    )
                    st.caption(f"Timestamp: `{switched_at}`")
                with c_badge:
                    st.success(f"Confidence: {float(conf):.0%}")

                st.markdown(f"**Reason / Rationale:**\n{reason}")
                st.divider()


# -------------------------------------------------------------
# TAB 2: New Hire Project Briefing
# -------------------------------------------------------------
with tab2:
    st.subheader("New Hire Project Briefing")

    try:
        res_briefs = (
            supabase.table("project_onboarding_briefs")
            .select("*")
            .order("generated_at", desc=True)
            .execute()
        )
        briefs = res_briefs.data or []
    except Exception:
        # Fallback without order if column differs
        try:
            res_briefs = supabase.table("project_onboarding_briefs").select("*").execute()
            briefs = res_briefs.data or []
        except Exception as e:
            st.error(f"Error fetching onboarding briefs: {e}")
            briefs = []

    available_projects = sorted(list({b.get("project_id") for b in briefs})) if briefs else ["Project-Alpha", "Project-Beta"]
    selected_proj = st.selectbox("Select Project", options=available_projects, index=0)

    proj_brief = next((b for b in briefs if b.get("project_id") == selected_proj), None)

    if not proj_brief:
        st.info(f"No synthesized briefing available for {selected_proj}.")
    else:
        # Executive Summary
        st.markdown("### Executive Summary")
        summary_text = proj_brief.get("raw_summary") or "No executive summary available."
        st.info(summary_text)

        col_left, col_right = st.columns(2)

        # Active Objectives
        with col_left:
            st.markdown("### Active Objectives")
            objectives = proj_brief.get("active_objectives") or []
            if isinstance(objectives, list) and objectives:
                for obj in objectives:
                    st.markdown(f"- {obj}")
            else:
                st.write("No active objectives recorded.")

        # Known Blockers
        with col_right:
            st.markdown("### Known Blockers")
            blockers = proj_brief.get("current_blockers") or []
            if isinstance(blockers, list) and blockers:
                blocker_text = "\n".join([f"- {b}" for b in blockers])
                st.warning(f"**Attention needed:**\n\n{blocker_text}")
            else:
                st.success("No active blockers identified.")

        st.markdown("### Recent Contributor Switches")
        switches_list = proj_brief.get("recent_switches") or []
        if isinstance(switches_list, list) and switches_list:
            for s in switches_list:
                st.markdown(f"- {s}")
        else:
            st.write("No recent contributor shifts.")


# -------------------------------------------------------------
# TAB 3: Raw Telemetry & Trace
# -------------------------------------------------------------
with tab3:
    st.subheader("Raw Telemetry & Trace")

    try:
        res_events = (
            supabase.table("developer_events")
            .select("*")
            .order("timestamp", desc=True)
            .limit(200)
            .execute()
        )
        raw_events = res_events.data or []
    except Exception as e:
        st.error(f"Error fetching telemetry logs: {e}")
        raw_events = []

    if not raw_events:
        st.info("No telemetry logs found.")
    else:
        df_events = pd.DataFrame(raw_events)

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            dev_options = ["All"] + sorted(list(df_events["developer_id"].dropna().unique()))
            selected_dev = st.selectbox("Filter by Developer", dev_options)
        with f_col2:
            tool_options = ["All"] + sorted(list(df_events["source_tool"].dropna().unique()))
            selected_tool = st.selectbox("Filter by Source Tool", tool_options)

        filtered_df = df_events.copy()
        if selected_dev != "All":
            filtered_df = filtered_df[filtered_df["developer_id"] == selected_dev]
        if selected_tool != "All":
            filtered_df = filtered_df[filtered_df["source_tool"] == selected_tool]

        latest_50 = filtered_df.head(50)
        st.caption(f"Displaying {len(latest_50)} most recent events")

        display_cols = [
            "timestamp",
            "developer_id",
            "project_id",
            "source_tool",
            "event_type",
            "content",
        ]
        available_display_cols = [c for c in display_cols if c in latest_50.columns]
        st.dataframe(latest_50[available_display_cols], use_container_width=True)

        with st.expander("Inspect Raw JSON for Filtered Records"):
            st.json(latest_50.to_dict(orient="records"))
