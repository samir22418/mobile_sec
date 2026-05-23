from __future__ import annotations

from datetime import datetime

import streamlit as st

from client import client


st.set_page_config(page_title="AEGIS Analyst Dashboard", layout="wide")


def risk_color(label: str) -> str:
    return {
        "Low": "#16a34a",
        "Watch": "#2563eb",
        "High": "#d97706",
        "Critical": "#dc2626",
    }.get(label, "#64748b")


def fmt_ms(value: int | None) -> str:
    if not value:
        return "--"
    return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M:%S")


def render_device_list() -> None:
    st.title("AEGIS Device Fleet")
    st.caption("Local analyst view for Android telemetry, risk, and feedback.")

    try:
        devices = client.get_devices()
    except Exception as error:
        st.error(f"Failed to connect to API: {error}")
        st.info("Check AEGIS_API_URL and AEGIS_ANALYST_TOKEN.")
        return

    if not devices:
        st.info("No devices have reported telemetry yet.")
        return

    header = st.columns([3, 1, 1, 1, 1])
    header[0].subheader("Device")
    header[1].subheader("Risk")
    header[2].subheader("Score")
    header[3].subheader("Payloads")
    header[4].subheader("Action")

    for device in devices:
        cols = st.columns([3, 1, 1, 1, 1])
        label = device.get("latest_risk_label", "UNKNOWN")
        cols[0].code(device["device_id"])
        cols[1].markdown(f"<b style='color:{risk_color(label)}'>{label}</b>", unsafe_allow_html=True)
        cols[2].write(device.get("latest_risk_score", 0))
        cols[3].write(device.get("payload_count", 0))
        if cols[4].button("Open", key=f"device:{device['device_id']}"):
            st.query_params["device_id"] = device["device_id"]
            st.rerun()


def render_device_details(device_id: str) -> None:
    if st.button("Back to fleet"):
        st.query_params.clear()
        st.rerun()

    st.title(f"Device {device_id}")
    try:
        latest_risk = client.get_device_latest_risk(device_id)
        timeline = client.get_device_timeline(device_id)
    except Exception as error:
        st.error(f"Failed to load device details: {error}")
        return

    if latest_risk:
        cols = st.columns(4)
        cols[0].metric("Risk", latest_risk["risk_label"])
        cols[1].metric("Score", latest_risk["risk_score"])
        cols[2].metric("Confidence", latest_risk["confidence"])
        cols[3].metric("Review", "Yes" if latest_risk["needs_human_review"] else "No")
        st.write("Recommended action:", latest_risk["recommended_action"])
        st.write("Reasons:")
        for reason in latest_risk.get("reasons", []):
            st.write(f"- {reason}")

    st.divider()
    st.header("Timeline")
    if not timeline:
        st.info("No telemetry found for this device.")
        return

    for item in timeline:
        # Timeline items are returned from the /latest-risk endpoint as RiskAssessment dictionaries.
        # They use 'created_at' (ISO string) instead of 'created_at_epoch_ms', and they do not have 'processing_status'.
        title = f"{item.get('created_at', '--')} | {item['payload_id']} | Risk: {item.get('risk_label', 'UNKNOWN')}"
        with st.expander(title):
            risk = item.get("risk") or item
            if risk.get("risk_label"):
                st.write(f"Risk: **{risk['risk_label']}** ({risk['risk_score']}/100)")
            if st.button("Inspect payload", key=f"payload:{item['payload_id']}"):
                st.query_params["payload_id"] = item["payload_id"]
                st.rerun()


def render_payload_details(payload_id: str) -> None:
    if st.button("Back"):
        st.query_params.pop("payload_id", None)
        st.rerun()

    st.title("Payload Analysis")
    st.code(payload_id)

    try:
        payload = client.get_payload(payload_id)
    except Exception as error:
        st.error(f"Failed to load payload: {error}")
        return

    if not payload:
        st.error("Payload not found.")
        return

    tab_risk, tab_apps, tab_logs, tab_ai = st.tabs(["Risk", "Apps", "Logs", "AI and Feedback"])

    with tab_risk:
        st.write("Processing status:", payload["processing_status"])
        risk = payload.get("risk_assessment")
        device_report = payload.get("device_report") or {}
        if risk:
            st.metric("Risk score", risk["risk_score"])
            st.write("Risk label:", risk["risk_label"])
            st.write("Recommended action:", risk["recommended_action"])
            for reason in risk.get("reasons", []):
                st.write(f"- {reason}")
        st.json(device_report)

    with tab_apps:
        apps = payload.get("apps", [])
        if not apps:
            st.info("No apps reported.")
        for app in apps:
            marker = "SUSPICIOUS" if app.get("is_suspicious") else "OK"
            st.write(f"**{app['package_name']}** - {marker}")
            st.caption(f"Source: {app['install_source']} | Version: {app.get('version_name') or '--'}")

    with tab_logs:
        logs = payload.get("logs", [])
        if not logs:
            st.info("No important logs reported.")
        for log in logs:
            st.code(f"[{log['level']}] {log['tag']}: {log['message_redacted']}")
            st.caption(f"Rule: {log['matched_rule']} | Hash: {log['message_hash']}")

    with tab_ai:
        ai_runs = payload.get("ai_runs", [])
        if not ai_runs:
            st.info("No AI analysis runs for this payload.")
        for run in ai_runs:
            st.subheader(run["model_used"])
            st.write("Status:", run["status"])
            st.write("Finding:", run["finding_summary"])
            st.json(run["output"])

            with st.form(key=f"feedback:{run['id']}"):
                label = st.selectbox(
                    "Feedback label",
                    ["TRUE_POSITIVE", "FALSE_POSITIVE", "BENIGN", "NEEDS_MORE_DATA"],
                )
                notes = st.text_area("Notes")
                if st.form_submit_button("Submit feedback"):
                    client.submit_feedback(str(run["id"]), label, notes, payload_id=payload_id)
                    st.success("Feedback submitted.")


def main() -> None:
    payload_id = st.query_params.get("payload_id")
    device_id = st.query_params.get("device_id")

    if payload_id:
        render_payload_details(payload_id)
    elif device_id:
        render_device_details(device_id)
    else:
        render_device_list()


if __name__ == "__main__":
    main()
