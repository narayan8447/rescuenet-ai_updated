"""
RescueNet AI - Streamlit Command Dashboard (frontend)

Run with:
    streamlit run frontend/app.py

Talks to the FastAPI backend over HTTP. Keeping the frontend in Streamlit
means the *entire* project - agents, backend, and dashboard - is Python,
matching the "multi-agent system built in Python only" requirement, while
still giving a real browser-based front end / back end split.
"""
import requests
import pandas as pd
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="RescueNet AI - Command Dashboard", layout="wide")

st.title("🚨 RescueNet AI — Disaster Response Command Center")
st.caption("Multi-agent AI system simulating coordinated disaster response (academic project).")

# ---------------------------------------------------------------- Sidebar --
with st.sidebar:
    st.header("Report a Disaster")
    disaster_type = st.selectbox(
        "Disaster type",
        ["flood", "earthquake", "cyclone", "fire", "landslide", "building_collapse"],
        format_func=lambda x: x.replace("_", " ").title(),
    )
    location_name = st.text_input("Location name", value="Delhi NCR")
    lat = st.number_input("Latitude", value=28.6139, format="%.4f")
    lon = st.number_input("Longitude", value=77.2090, format="%.4f")

    trigger = st.button("🚀 Trigger Disaster Response Pipeline", use_container_width=True, type="primary")

    st.divider()
    if st.button("🔄 Reset simulated resources", use_container_width=True):
        try:
            requests.post(f"{API_BASE}/api/reset", timeout=5)
            st.success("State reset to defaults.")
        except requests.exceptions.ConnectionError:
            st.error("Backend not reachable. Is uvicorn running on port 8000?")

    st.divider()
    st.caption(
        "Backend must be running separately:\n\n"
        "`uvicorn backend.main:app --reload --port 8000`"
    )

tab_live, tab_history, tab_state = st.tabs(["🟢 Live Response", "🕓 Incident History", "📊 Live Resource State"])

# ------------------------------------------------------------- Live tab ---
with tab_live:
    if trigger:
        payload = {
            "disaster_type": disaster_type,
            "location_name": location_name,
            "lat": lat,
            "lon": lon,
        }
        try:
            with st.spinner("Running multi-agent pipeline..."):
                resp = requests.post(f"{API_BASE}/api/disaster/trigger", json=payload, timeout=30)
            if resp.status_code != 200:
                st.error(f"Backend error {resp.status_code}: {resp.text}")
            else:
                st.session_state["report"] = resp.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot reach backend at http://127.0.0.1:8000. Start it with:\n\n`uvicorn backend.main:app --reload --port 8000`")

    report = st.session_state.get("report")

    if not report:
        st.info("Configure a disaster in the sidebar and click **Trigger Disaster Response Pipeline** to run the agents.")
    else:
        event = report["event"]
        st.success(
            f"**{event['disaster_type'].replace('_',' ').title()}** detected in **{event['location_name']}** "
            f"— confidence {event['confidence']*100:.1f}%"
        )
        st.markdown(f"### 📋 Situation Summary\n{report['narrative_summary']}")

        st.markdown("### 🗺️ Affected Area & Facilities")
        map_points = []
        map_points.append({"lat": event["lat"], "lon": event["lon"], "label": "Epicentre"})
        for d in report["damage_reports"]:
            map_points.append({"lat": d["lat"], "lon": d["lon"], "label": d["area_id"]})
        for p in report["priorities"]:
            map_points.append({"lat": p["lat"], "lon": p["lon"], "label": p["entity"]})
        st.map(pd.DataFrame(map_points)[["lat", "lon"]], size=40)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🎯 Rescue Priorities")
            st.dataframe(pd.DataFrame(report["priorities"])[["entity", "entity_type", "priority_score", "reason"]],
                         use_container_width=True, hide_index=True)

            st.markdown("### 🚑 Resource Assignments")
            st.dataframe(pd.DataFrame(report["resource_assignments"]), use_container_width=True, hide_index=True)

            st.markdown("### 🛣️ Route Plans")
            st.dataframe(pd.DataFrame(report["routes"]), use_container_width=True, hide_index=True)

            st.markdown("### 🏥 Hospital Assignments")
            st.dataframe(pd.DataFrame(report["hospital_assignments"]), use_container_width=True, hide_index=True)

        with col2:
            st.markdown("### 🏕️ Shelter Assignments")
            st.dataframe(pd.DataFrame(report["shelter_assignments"]), use_container_width=True, hide_index=True)

            st.markdown("### 📦 Relief Distribution Plan")
            st.dataframe(pd.DataFrame(report["relief_plan"]), use_container_width=True, hide_index=True)

            st.markdown("### 🙋 Volunteer Assignments")
            st.dataframe(pd.DataFrame(report["volunteer_assignments"]), use_container_width=True, hide_index=True)

            st.markdown("### 📈 Forecasts (Prediction Agent)")
            st.dataframe(pd.DataFrame(report["forecasts"]), use_container_width=True, hide_index=True)

        st.markdown("### 📢 Public Alerts")
        alert_cols = st.columns(2)
        seen_langs = []
        for a in report["alerts"]:
            if a["language"] not in seen_langs:
                seen_langs.append(a["language"])
        for i, lang in enumerate(seen_langs):
            with alert_cols[i % 2]:
                st.markdown(f"**{lang}**")
                sample = next(a for a in report["alerts"] if a["language"] == lang)
                st.info(sample["message"])
                channels = [a["channel"] for a in report["alerts"] if a["language"] == lang]
                st.caption("Sent via: " + ", ".join(channels))

        st.markdown("### 🧠 Agent-by-Agent Trace")
        for step in report["trace"]:
            with st.expander(f"**{step['agent']}** — {step['summary']}"):
                st.json(step["data"])

# ---------------------------------------------------------- History tab --
with tab_history:
    st.markdown("### Past Incidents")
    try:
        incidents = requests.get(f"{API_BASE}/api/incidents", timeout=10).json()
    except requests.exceptions.ConnectionError:
        incidents = None
        st.error("Backend not reachable.")

    if incidents:
        df = pd.DataFrame(incidents)
        st.dataframe(df, use_container_width=True, hide_index=True)
        chosen = st.selectbox("View full report for incident #", df["id"].tolist())
        if st.button("Load report"):
            detail = requests.get(f"{API_BASE}/api/incidents/{chosen}", timeout=10).json()
            st.json(detail["report"])
    elif incidents == []:
        st.info("No incidents triggered yet.")

# -------------------------------------------------------------- State tab-
with tab_state:
    st.markdown("### Live Resource / Facility State")
    try:
        state = requests.get(f"{API_BASE}/api/state", timeout=10).json()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Hospitals**")
            st.dataframe(pd.DataFrame(state["hospitals"]), use_container_width=True, hide_index=True)
            st.markdown("**Shelters**")
            st.dataframe(pd.DataFrame(state["shelters"]), use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**Volunteers**")
            st.dataframe(pd.DataFrame(state["volunteers"]), use_container_width=True, hide_index=True)
            st.markdown("**Resources (fleet)**")
            for rtype, items in state["resources"].items():
                st.caption(rtype.replace("_", " ").title())
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    except requests.exceptions.ConnectionError:
        st.error("Backend not reachable.")
