import streamlit as st
import pandas as pd
from frontend.api_client import ApiClient, ApiError


def render_contractor_view():
    user = st.session_state.get("user", {})
    st.markdown(f"## 🔧 Contractor Workspace — {user.get('full_name', 'Contractor')}")
    st.markdown("View and service your assigned repair requests with server-enforced lifecycle rules.")

    # 1. Summary Metrics
    try:
        dash = ApiClient.get_contractor_dashboard()
    except ApiError as e:
        st.error(f"Failed to load contractor dashboard: {e.detail}")
        return

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Assigned Tickets</div>
                <div class="metric-value">{dash['assigned_requests_count']}</div>
                <div class="metric-sub">Total assigned to you</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Open Tickets</div>
                <div class="metric-value" style="color: #2563eb;">{dash['open_requests_count']}</div>
                <div class="metric-sub">Pending work</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">High Priority</div>
                <div class="metric-value" style="color: {'#dc2626' if dash['high_priority_count'] > 0 else '#475569'};">{dash['high_priority_count']}</div>
                <div class="metric-sub">Urgent repairs</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with k4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Resolved</div>
                <div class="metric-value" style="color: #059669;">{dash['resolved_requests_count']}</div>
                <div class="metric-sub">Completed work</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    tab_my_requests, tab_create = st.tabs(["📋 My Assigned Requests", "➕ Log New Maintenance Request"])

    # --- TAB 1: My Requests ---
    with tab_my_requests:
        try:
            # Server strictly limits contractor to their assigned requests
            res = ApiClient.get_maintenance_requests(page_size=50)
            my_requests = res["items"]
        except ApiError as e:
            st.error(f"Error fetching assigned requests: {e.detail}")
            return

        if not my_requests:
            st.info("You currently have no maintenance requests assigned to you.")
        else:
            table_rows = []
            for r in my_requests:
                table_rows.append({
                    "ID": r["id"],
                    "Unit": r["unit_number"],
                    "Address": r["unit_address"],
                    "Priority": r["priority"],
                    "Status": r["status"],
                    "Description": r["description"][:50] + ("..." if len(r["description"]) > 50 else ""),
                    "Assigned Since": r["created_at"][:10]
                })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("##### 🔍 Service Ticket Inspector")
            req_map = {f"#{r['id']} · Unit {r['unit_number']} · {r['description'][:40]}": r["id"] for r in my_requests}
            selected_label = st.selectbox("Select ticket to service:", options=list(req_map.keys()), key="contractor_req_sel")
            selected_id = req_map[selected_label]

            try:
                ticket = ApiClient.get_maintenance_request(selected_id)
            except ApiError as e:
                st.error(f"Failed to fetch ticket: {e.detail}")
                return

            c_left, c_right = st.columns([1, 1])

            with c_left:
                st.markdown(f"#### Ticket #{ticket['id']} — Unit {ticket['unit_number']}")
                st.markdown(f"**Location:** {ticket['unit_address']}")
                st.markdown(
                    f"""
                    <div>
                        <strong>Priority:</strong> <span class="badge badge-{ticket['priority'].lower()}">{ticket['priority']}</span>
                        &nbsp;&nbsp;
                        <strong>Current Status:</strong> <span class="badge badge-{ticket['status'].lower()}">{ticket['status']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("---")
                st.markdown("###### 🔄 Advance Lifecycle Status")
                st.caption("Valid transitions: Reported → Triaged → Scheduled → Resolved → Triaged.")

                status_options = ["REPORTED", "TRIAGED", "SCHEDULED", "RESOLVED"]
                new_status = st.selectbox(
                    "Select New Status",
                    options=status_options,
                    index=status_options.index(ticket["status"]),
                    key=f"contractor_status_{ticket['id']}"
                )
                trans_note = st.text_input("Completion / Progress Note", placeholder="e.g. Completed faucet repair and checked water pressure", key=f"contractor_note_{ticket['id']}")

                if st.button("Update Status", type="primary", key=f"btn_c_status_{ticket['id']}"):
                    try:
                        ApiClient.update_maintenance_status(ticket["id"], new_status, trans_note if trans_note.strip() else None)
                        st.success(f"Status updated to {new_status}!")
                        st.rerun()
                    except ApiError as e:
                        st.error(f"Transition Rejected: {e.detail}")

                st.markdown("---")
                st.markdown("###### ✏️ Edit Description & Priority")
                with st.form(f"contractor_edit_{ticket['id']}"):
                    edit_desc = st.text_area("Description", value=ticket["description"])
                    edit_priority = st.selectbox("Priority", options=["LOW", "MEDIUM", "HIGH"], index=["LOW", "MEDIUM", "HIGH"].index(ticket["priority"]))
                    if st.form_submit_button("Save Changes"):
                        try:
                            ApiClient.update_maintenance_details(ticket["id"], description=edit_desc.strip(), priority=edit_priority)
                            st.success("Details updated!")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Failed to update details: {e.detail}")

                st.markdown("---")
                st.markdown("###### 📝 Add Timeline Progress Note")
                c_note = st.text_area("Add note", placeholder="Parts status, inspection findings, notes...", height=70, key=f"c_note_{ticket['id']}")
                if st.button("Add Note", key=f"btn_c_add_note_{ticket['id']}"):
                    if not c_note.strip():
                        st.warning("Note cannot be empty.")
                    else:
                        try:
                            ApiClient.add_maintenance_note(ticket["id"], c_note.strip())
                            st.success("Note added to permanent timeline!")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Failed to add note: {e.detail}")

            with c_right:
                st.markdown("#### 📜 Ticket Timeline")
                st.caption("Permanent record of all actions taken on this ticket.")
                timeline_events = ticket.get("timeline_events", [])
                if not timeline_events:
                    st.info("No timeline events.")
                else:
                    st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
                    for event in timeline_events:
                        actor_info = f"{event.get('actor_name') or 'System'} ({event.get('actor_role') or 'System'})"
                        time_str = event["created_at"][:19].replace("T", " ")
                        event_type = event["event_type"]

                        header_text = f"<strong>{event_type}</strong> by {actor_info}"
                        body_content = ""

                        if event.get("old_value") and event.get("new_value"):
                            body_content += f"Changed from <code>{event['old_value']}</code> ➔ <code>{event['new_value']}</code><br>"
                        elif event.get("new_value"):
                            body_content += f"Value: <code>{event['new_value']}</code><br>"

                        if event.get("note"):
                            body_content += f"<div style='margin-top: 0.3rem; color: #1e293b;'>{event['note']}</div>"

                        st.markdown(
                            f"""
                            <div class="timeline-item">
                                <div class="timeline-dot"></div>
                                <div class="timeline-header">{header_text}</div>
                                <div class="timeline-time">{time_str} UTC</div>
                                <div class="timeline-body">{body_content or 'No additional details.'}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 2: Log New Request ---
    with tab_create:
        st.markdown("##### Log New Maintenance Request")
        try:
            # Contractor gets basic unit list without rent data
            units = ApiClient.get_units(include_archived=False)
            unit_map = {f"Unit {u['unit_number']} — {u['address']}": u["id"] for u in units}
        except ApiError:
            unit_map = {}

        if not unit_map:
            st.info("No units available.")
        else:
            with st.form("contractor_create_form"):
                target_label = st.selectbox("Unit", options=list(unit_map.keys()))
                target_id = unit_map[target_label]
                desc = st.text_area("Issue Description", placeholder="Describe the issue discovered on-site...", height=100)
                priority = st.selectbox("Priority Level", options=["LOW", "MEDIUM", "HIGH"], index=1)
                submit_req = st.form_submit_button("Submit Request", type="primary")

                if submit_req:
                    if len(desc.strip()) < 3:
                        st.error("Description must be at least 3 characters.")
                    else:
                        try:
                            created = ApiClient.create_maintenance_request(target_id, desc.strip(), priority)
                            st.success(f"Request #{created['id']} logged! Property Manager will triage and assign.")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Failed to submit: {e.detail}")
