from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean

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


def is_high_risk(device: dict) -> bool:
    label = str(device.get("latest_risk_label", "")).lower()
    score = int(device.get("latest_risk_score") or 0)
    return label in {"high", "critical"} or score >= 50


def render_overview(devices: list[dict]) -> None:
    total_payloads = sum(int(device.get("payload_count") or 0) for device in devices)
    scores = [int(device.get("latest_risk_score") or 0) for device in devices]
    high_risk = [device for device in devices if is_high_risk(device)]

    cols = st.columns(4)
    cols[0].metric("Active devices", len(devices))
    cols[1].metric("Total payloads", total_payloads)
    cols[2].metric("High risk", len(high_risk))
    cols[3].metric("Average risk", f"{mean(scores):.1f}" if scores else "0.0")


def render_risk_distribution(devices: list[dict]) -> None:
    st.subheader("Risk Distribution")
    labels = ["Low", "Watch", "High", "Critical", "UNKNOWN"]
    counts = Counter(device.get("latest_risk_label", "UNKNOWN") for device in devices)
    total = max(len(devices), 1)

    for label in labels:
        count = counts.get(label, 0)
        if count == 0:
            continue
        st.markdown(
            f"<span style='color:{risk_color(label)};font-weight:700'>{label}</span> "
            f"<span style='color:#617089'>({count})</span>",
            unsafe_allow_html=True,
        )
        st.progress(count / total)


def render_high_risk_devices(devices: list[dict]) -> None:
    st.subheader("Priority Devices")
    priority = sorted(
        [device for device in devices if is_high_risk(device)],
        key=lambda device: int(device.get("latest_risk_score") or 0),
        reverse=True,
    )[:5]

    if not priority:
        st.success("No high-risk devices right now.")
        return

    for device in priority:
        cols = st.columns([3, 1, 2])
        label = device.get("latest_risk_label", "UNKNOWN")
        cols[0].code(device["device_id"])
        cols[1].markdown(f"<b style='color:{risk_color(label)}'>{label}</b>", unsafe_allow_html=True)
        cols[2].write(f"Score {device.get('latest_risk_score', 0)}")


def render_fleet_trend(devices: list[dict]) -> None:
    trend: dict[str, list[int]] = defaultdict(list)
    for device in devices:
        try:
            timeline = client.get_device_timeline(device["device_id"])
        except Exception:
            continue
        for item in timeline:
            risk = item.get("risk") or item
            score = risk.get("risk_score")
            created_at = risk.get("created_at") or item.get("received_at")
            if score is None or not created_at:
                continue
            day = created_at[:10]
            trend[day].append(int(score))

    st.subheader("Risk Trend")
    if not trend:
        st.info("Trend appears after devices send scored telemetry.")
        return

    chart_data = {
        day: round(mean(scores), 1)
        for day, scores in sorted(trend.items())
    }
    st.line_chart({"Average risk": chart_data})


def severity_color(level: str) -> str:
    return {
        "ASSERT": "#dc2626",
        "ERROR": "#dc2626",
        "WARN": "#d97706",
        "INFO": "#2563eb",
        "DEBUG": "#64748b",
        "VERBOSE": "#64748b",
    }.get(level, "#64748b")


def fmt_epoch_ms(value: int | None) -> str:
    if not value:
        return "--"
    return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M:%S")


def render_logs_analyzer(devices: list[dict] | None = None) -> None:
    st.title("Logs Analyzer")
    st.caption("Redacted security log signals, repeated patterns, and device pressure.")

    device_options = ["All devices"]
    if devices:
        device_options += [device["device_id"] for device in devices]
    selected_device = st.selectbox("Scope", device_options, index=0)
    scoped_device = None if selected_device == "All devices" else selected_device
    f1, f2, f3 = st.columns([1, 1, 2])
    selected_level = f1.selectbox(
        "Level",
        ["All", "ASSERT", "ERROR", "WARN", "INFO", "DEBUG", "VERBOSE", "UNKNOWN"],
    )
    selected_rule = f2.selectbox(
        "Rule",
        ["All", "THREAT_REGEX", "LEVEL_ERROR_OR_ASSERT", "TAG_KEYWORD"],
    )
    search_text = f3.text_input("Search tag, device, payload, hash, or redacted message")

    try:
        analysis = client.get_logs_analysis(
            device_id=scoped_device,
            level=None if selected_level == "All" else selected_level,
            matched_rule=None if selected_rule == "All" else selected_rule,
            q=search_text.strip() or None,
            limit=80,
        )
    except Exception as error:
        st.error(f"Failed to load logs analysis: {error}")
        return

    summary = analysis.get("summary", {})
    cols = st.columns(5)
    cols[0].metric("Logs", summary.get("total_logs", 0))
    cols[1].metric("High severity", summary.get("high_severity_count", 0))
    cols[2].metric("Threat regex", summary.get("threat_regex_count", 0))
    cols[3].metric("Repeated clusters", summary.get("repeated_clusters", 0))
    cols[4].metric("Devices", summary.get("affected_devices", 0))

    left, middle, right = st.columns([1, 1, 1])
    with left:
        st.subheader("Severity Mix")
        by_level = analysis.get("by_level", {})
        total = max(sum(by_level.values()), 1)
        if not by_level:
            st.info("No logs yet.")
        for level, count in by_level.items():
            st.markdown(
                f"<span style='color:{severity_color(level)};font-weight:700'>{level}</span> "
                f"<span style='color:#617089'>({count})</span>",
                unsafe_allow_html=True,
            )
            st.progress(count / total)

    with middle:
        st.subheader("Rule Signals")
        by_rule = analysis.get("by_rule", {})
        total_rules = max(sum(by_rule.values()), 1)
        if not by_rule:
            st.info("No matched rules yet.")
        for rule, count in by_rule.items():
            st.write(f"**{rule}**")
            st.progress(count / total_rules)

    with right:
        st.subheader("Device Pressure")
        top_devices = analysis.get("top_devices", [])
        if not top_devices:
            st.info("No device log pressure yet.")
        for device in top_devices[:5]:
            st.code(device["device_id"])
            st.caption(f"{device['count']} important log(s)")

    timeline = analysis.get("timeline", [])
    st.subheader("Log Pulse")
    if timeline:
        st.line_chart({
            "Total logs": {item["day"]: item["total"] for item in timeline},
            "High severity": {item["day"]: item["high_severity"] for item in timeline},
        })
    else:
        st.info("Timeline appears after important logs arrive.")

    st.subheader("Repeated Message Clusters")
    clusters = analysis.get("clusters", [])
    if not clusters:
        st.success("No repeated redacted-message clusters detected.")
    for cluster in clusters:
        with st.expander(f"{cluster['count']} hits | {cluster['sample_message'][:96]}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Devices", len(cluster.get("devices", [])))
            c2.metric("First seen", fmt_epoch_ms(cluster.get("first_seen_epoch_ms")))
            c3.metric("Last seen", fmt_epoch_ms(cluster.get("last_seen_epoch_ms")))
            st.write("Tags:", cluster.get("tags", {}))
            st.write("Levels:", cluster.get("levels", {}))
            st.code(cluster["message_hash"])

    st.subheader("Top Tags")
    top_tags = analysis.get("top_tags", [])
    if top_tags:
        tag_data = {item["tag"]: item["count"] for item in top_tags}
        st.bar_chart({"count": tag_data})
    else:
        st.info("No top tags yet.")

    st.subheader("Recent Redacted Stream")
    recent = analysis.get("recent_logs", [])
    if not recent:
        st.info("No recent important logs.")
        return
    for log in recent:
        badge = log["level"]
        st.markdown(
            f"<b style='color:{severity_color(badge)}'>{badge}</b> "
            f"<code>{log['tag']}</code> "
            f"<span style='color:#617089'>{fmt_epoch_ms(log.get('observed_at_epoch_ms'))}</span>",
            unsafe_allow_html=True,
        )
        st.code(log["message_redacted"])
        st.caption(
            f"Device {log['device_id']} | Payload {log['payload_id']} | "
            f"Rule {log['matched_rule']} | Hash {log['message_hash'][:12]}"
        )


def render_ai_center(devices: list[dict] | None = None) -> None:
    st.title("AI Center")
    st.caption("Local analyzers, AI risk decisions, and the Shieldy/OpenRouter action assistant.")

    device_options = ["All devices"]
    if devices:
        device_options += [device["device_id"] for device in devices]
    selected_device = st.selectbox("AI device scope", device_options, index=0)
    scoped_device = None if selected_device == "All devices" else selected_device
    role = st.selectbox(
        "Model role",
        ["All", "logs_llm_analyst", "telemetry_llm_analyst", "risk_llm_scorer", "primary_llm_analyst"],
    )

    try:
        runs = client.get_ai_runs(
            device_id=scoped_device,
            role=None if role == "All" else role,
            limit=50,
        )
    except Exception as error:
        st.error(f"Failed to load AI runs: {error}")
        runs = []

    cols = st.columns(4)
    cols[0].metric("Model runs", len(runs))
    cols[1].metric("Failed", sum(1 for run in runs if run.get("status") == "FAILED"))
    cols[2].metric("Risk scorers", sum(1 for run in runs if run.get("model_role") == "risk_llm_scorer"))
    cols[3].metric("Providers", len({run.get("provider") for run in runs if run.get("provider")}))

    runs_tab, decisions_tab, chat_tab, handoff_tab = st.tabs([
        "Model Runs",
        "Risk Decisions",
        "Shieldy Chat",
        "AI Engineering",
    ])

    payload_options = [""] + sorted({run["payload_id"] for run in runs if run.get("payload_id")})

    with runs_tab:
        st.subheader("Recent AI Runs")
        if not runs:
            st.info("AI runs appear after Watch, High, or Critical payloads are processed.")
        for run in runs[:12]:
            title = f"{run['model_role']} | {run['status']} | {run['payload_id']}"
            with st.expander(title):
                st.write("Provider:", run.get("provider", "--"))
                st.write("Model:", run.get("model_name", "--"))
                st.write("Latency:", f"{run.get('latency_ms', 0)} ms")
                st.json(run.get("output", {}))

    with decisions_tab:
        st.subheader("Risk Decision")
        selected_payload = st.selectbox("Payload decision", payload_options)
        if selected_payload:
            try:
                decision_payload = client.get_ai_decision(selected_payload)
            except Exception as error:
                st.error(f"Failed to load decision: {error}")
                decision_payload = None
            if decision_payload:
                decision = decision_payload["decision"]
                c1, c2 = st.columns(2)
                c1.metric("Deterministic", decision["deterministic_score"], decision["deterministic_label"])
                c2.metric("Final AI", decision["final_score"], decision["final_label"])
                st.write("Recommended action:", decision["recommended_action"])
                st.write("Evidence refs:", ", ".join(decision.get("evidence_refs", [])))
                st.json(decision)
        else:
            st.info("Pick a payload to compare deterministic baseline with AI final risk.")

    with chat_tab:
        st.subheader("Shieldy Action Assistant")
        st.caption("Uses Shieldy-style safety, routing, model roles, memory-by-session, and confirm-before-action tools.")
        if "chat_session_id" not in st.session_state:
            st.session_state.chat_session_id = None
        if st.button("New Shieldy chat") or not st.session_state.chat_session_id:
            try:
                chat = client.create_chat_session()
                st.session_state.chat_session_id = chat["id"]
                st.session_state.chat_messages = []
                st.session_state.chat_actions = []
            except Exception as error:
                st.error(f"Failed to create chat session: {error}")
                return

        context_payload = st.selectbox("Selected payload context", payload_options, key="chat_context")
        prompt = st.text_area("Ask Shieldy")
        if st.button("Send to Shieldy") and prompt.strip():
            try:
                response = client.send_chat_message(
                    st.session_state.chat_session_id,
                    prompt.strip(),
                    context_payload_id=context_payload or None,
                )
                st.session_state.chat_messages = st.session_state.get("chat_messages", []) + [
                    {"role": "user", "content": prompt.strip()},
                    response["message"],
                ]
                st.session_state.chat_actions = response.get("actions", [])
                st.session_state.chat_route = response.get("route")
                st.session_state.chat_safety = response.get("safety")
            except Exception as error:
                st.error(f"Assistant failed: {error}")

        status_cols = st.columns(2)
        status_cols[0].metric("Route", st.session_state.get("chat_route") or "--")
        safety = st.session_state.get("chat_safety") or {}
        status_cols[1].metric("Safety", safety.get("action", "--"), safety.get("reason", ""))

        for message in st.session_state.get("chat_messages", []):
            st.write(f"**{message.get('role', 'assistant').title()}**")
            st.write(message.get("content", ""))

        for action in st.session_state.get("chat_actions", []):
            st.warning(f"Pending action: {action['tool_name']}")
            st.json(action.get("payload", {}))
            if st.button("Confirm action", key=f"confirm:{action['id']}"):
                try:
                    result = client.confirm_chat_action(action["id"])
                    st.success(f"Action completed: {result['status']}")
                    st.json(result)
                except Exception as error:
                    st.error(f"Action failed: {error}")

    with handoff_tab:
        st.subheader("Replaceable AI Architecture")
        st.write("Local analyzers are isolated behind provider classes for logs, telemetry, and risk scoring.")
        st.write("Shieldy chat is isolated under the backend Shieldy module: models, safety gate, fast router, prompts, providers, and agent.")
        st.write("AI engineers can replace local providers, prompts, routes, and scoring validators without changing ingestion or Android telemetry.")


def render_device_list() -> None:
    st.title("AEGIS SOC Dashboard")
    st.caption("Mobile security posture, risk, and analyst review.")

    try:
        devices = client.get_devices()
    except Exception as error:
        st.error(f"Failed to connect to API: {error}")
        st.info("Check AEGIS_API_URL and AEGIS_ANALYST_TOKEN.")
        return

    if not devices:
        st.info("No devices have reported telemetry yet.")
        return

    fleet_tab, logs_tab, ai_tab = st.tabs(["Fleet Overview", "Logs Analyzer", "AI Center"])
    with logs_tab:
        render_logs_analyzer(devices)
    with ai_tab:
        render_ai_center(devices)
    with fleet_tab:
        render_fleet_overview(devices)


def render_fleet_overview(devices: list[dict]) -> None:
    render_overview(devices)
    left, right = st.columns([1, 1])
    with left:
        render_risk_distribution(devices)
    with right:
        render_high_risk_devices(devices)
    render_fleet_trend(devices)
    st.divider()
    st.subheader("Device Fleet")

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
        ai_decision = payload.get("ai_decision")
        if ai_decision:
            st.write("AI decision:")
            d1, d2 = st.columns(2)
            d1.metric("Deterministic", ai_decision["deterministic_score"], ai_decision["deterministic_label"])
            d2.metric("AI final", ai_decision["final_score"], ai_decision["final_label"])
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
