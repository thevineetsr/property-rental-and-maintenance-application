import streamlit as st
import pandas as pd
from frontend.api_client import ApiClient, ApiError


def render_maintenance_view():
    st.markdown("## 🛠️ Maintenance Operations")
    st.markdown("Track and triage repair requests across all units with server-enforced lifecycle rules and immutable history.")

    tab_list, tab_create = st.tabs(["🔍 Search & Manage Requests", "➕ Log New Request"])

    # --- TAB 1: Search & Manage ---
    with tab_list:
        # 1. Search & Filter Bar (Executed completely on the server)
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            search_query = st.text_input("Search Description or Unit", placeholder="e.g. pipe, leak, 101", key="maint_search")
        with f2:
            status_filter = st.selectbox("Status Filter", options=["All", "REPORTED", "TRIAGED", "SCHEDULED", "RESOLVED"], key="maint_status")
        with f3:
            priority_filter = st.selectbox("Priority Filter", options=["All", "LOW", "MEDIUM", "HIGH"], key="maint_priority")
        with f4:
            sort_by = st.selectbox("Sort By", options=["created_at", "priority", "status"], index=0, key="maint_sort")

        p1, p2, p3 = st.columns([1, 2, 1])
        with p1:
            sort_order = st.selectbox("Order", options=["desc", "asc"], index=0, key="maint_order")
        with p2:
            page_num = st.number_input("Page", min_value=1, value=1, step=1, key="maint_page")
        with p3:
            page_size = st.selectbox("Page Size", options=[10, 20, 50], index=1, key="maint_size")

        # Load filtered requests from server
        try:
            res = ApiClient.get_maintenance_requests(
                query=search_query if search_query.strip() else None,
                status=None if status_filter == "All" else status_filter,
                priority=None if priority_filter == "All" else priority_filter,
                sort_by=sort_by,
                sort_order=sort_order,
                page=page_num,
                page_size=page_size
            )
            items = res["items"]
            total_items = res["total"]
            total_pages = res["total_pages"]
        except ApiError as e:
            st.error(f"Failed to retrieve requests: {e.detail}")
            return

        st.caption(f"Showing {len(items)} of {total_items} matching requests (Page {page_num} of {total_pages})")

        if not items:
            st.info("No maintenance requests match your search criteria.")
        else:
            table_rows = []
            for r in items:
                assigned_names = ", ".join([c["full_name"] for c in r["assigned_contractors"]]) or "— None —"
                table_rows.append({
                    "ID": r["id"],
                    "Unit": r["unit_number"],
                    "Priority": r["priority"],
                    "Status": r["status"],
                    "Contractors": assigned_names,
                    "Description": r["description"][:50] + ("..." if len(r["description"]) > 50 else ""),
                    "Created": r["created_at"][:10]
                })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("##### 📌 Request Detail & Workflow Inspector")
            req_options = {f"#{r['id']} · Unit {r['unit_number']} · {r['description'][:35]}": r["id"] for r in items}
            selected_label = st.selectbox("Select request to inspect:", options=list(req_options.keys()))
            selected_id = req_options[selected_label]

            try:
                req = ApiClient.get_maintenance_request(selected_id)
            except ApiError as e:
                st.error(f"Failed to fetch request #{selected_id}: {e.detail}")
                return

            col_detail, col_timeline = st.columns([1, 1])

            # Left Column: Details, Status Transition, Contractor Assignment
            with col_detail:
                st.markdown(f"#### Request #{req['id']} — Unit {req['unit_number']}")
                st.markdown(f"**Address:** {req['unit_address']}")
                st.markdown(f"**Description:** {req['description']}")
                st.markdown(
                    f"""
                    <div>
                        <strong>Priority:</strong> <span class="badge badge-{req['priority'].lower()}">{req['priority']}</span>
                        &nbsp;&nbsp;
                        <strong>Status:</strong> <span class="badge badge-{req['status'].lower()}">{req['status']}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.4rem;">
                        Logged by: {req['creator_name']} on {req['created_at'][:19].replace('T', ' ')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("---")
                # 2. Lifecycle Status Stepper
                st.markdown("###### 🔄 Advance Lifecycle Status")
                st.caption("Valid transitions: Reported → Triaged → Scheduled (requires contractor) → Resolved → Triaged (reopen).")

                status_options = ["REPORTED", "TRIAGED", "SCHEDULED", "RESOLVED"]
                new_status = st.selectbox(
                    "Target Status",
                    options=status_options,
                    index=status_options.index(req["status"]),
                    key=f"status_sel_{req['id']}"
                )
                status_note = st.text_input("Transition Note / Reason", placeholder="e.g. Assigned contractor & confirmed parts", key=f"note_sel_{req['id']}")

                if st.button("Update Status", type="primary", key=f"btn_status_{req['id']}"):
                    try:
                        ApiClient.update_maintenance_status(req["id"], new_status, status_note if status_note.strip() else None)
                        st.success(f"Status successfully updated to {new_status}!")
                        st.rerun()
                    except ApiError as e:
                        st.error(f"Status Transition Rejected: {e.detail}")

                st.markdown("---")
                # 3. Contractor Assignment (Manager Only)
                st.markdown("###### 👷 Contractor Assignment")
                try:
                    all_contractors = ApiClient.get_contractors()
                    contractor_map = {f"{c['full_name']} ({c['email']})": c["id"] for c in all_contractors}
                    currently_assigned_ids = [c["id"] for c in req["assigned_contractors"]]
                    default_selected = [k for k, v in contractor_map.items() if v in currently_assigned_ids]

                    chosen_contractors = st.multiselect(
                        "Assigned Contractors (M:N)",
                        options=list(contractor_map.keys()),
                        default=default_selected,
                        key=f"assign_contractors_{req['id']}"
                    )

                    if st.button("Save Contractor Assignment", key=f"btn_save_contractors_{req['id']}"):
                        chosen_ids = [contractor_map[k] for k in chosen_contractors]
                        try:
                            ApiClient.assign_contractors(req["id"], chosen_ids)
                            st.success("Contractors updated successfully!")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Assignment failed: {e.detail}")
                except ApiError as e:
                    st.error(f"Failed to load contractors: {e.detail}")

                st.markdown("---")
                # 4. Add Permanent Timeline Note
                st.markdown("###### 📝 Add Timeline Note")
                new_note = st.text_area("Note content", placeholder="Add progress report or note for permanent record...", height=70, key=f"note_area_{req['id']}")
                if st.button("Post Note", key=f"btn_note_{req['id']}"):
                    if not new_note.strip():
                        st.warning("Note cannot be empty.")
                    else:
                        try:
                            ApiClient.add_maintenance_note(req["id"], new_note.strip())
                            st.success("Note added to timeline!")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Failed to add note: {e.detail}")

            # Right Column: Immutable Timeline Audit Trail
            with col_timeline:
                st.markdown("#### 📜 Immutable History Timeline")
                st.caption("Permanent record of creation, status changes, assignments, and notes. Cannot be edited or deleted.")

                timeline_events = req.get("timeline_events", [])
                if not timeline_events:
                    st.info("No timeline events recorded.")
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
            units = ApiClient.get_units(include_archived=False)
            unit_map = {f"Unit {u['unit_number']} — {u['address']}": u["id"] for u in units}
        except ApiError:
            unit_map = {}

        if not unit_map:
            st.info("No units available.")
        else:
            with st.form("create_maintenance_form"):
                target_unit_label = st.selectbox("Unit", options=list(unit_map.keys()))
                target_unit_id = unit_map[target_unit_label]
                desc = st.text_area("Issue Description", placeholder="Describe the maintenance or repair issue in detail...", height=100)
                priority = st.selectbox("Priority Level", options=["LOW", "MEDIUM", "HIGH"], index=1)
                submit_req = st.form_submit_button("Submit Maintenance Request", type="primary")

                if submit_req:
                    if len(desc.strip()) < 3:
                        st.error("Please provide a meaningful description (at least 3 characters).")
                    else:
                        try:
                            created = ApiClient.create_maintenance_request(target_unit_id, desc.strip(), priority)
                            st.success(f"Maintenance request #{created['id']} logged in REPORTED status!")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Failed to create request: {e.detail}")
