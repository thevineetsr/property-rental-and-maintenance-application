import streamlit as st
import pandas as pd
from frontend.api_client import ApiClient, ApiError


def render_units_view():
    st.markdown("## 🏢 Unit Management")
    st.markdown("Manage property units, tenants, lease pricing, and lifecycle archiving.")

    tab_active, tab_archived, tab_add = st.tabs(["Active Portfolio", "Archived Units", "➕ Add New Unit"])

    # --- TAB 1: Active Units ---
    with tab_active:
        try:
            active_units = ApiClient.get_units(include_archived=False)
        except ApiError as e:
            st.error(f"Error loading units: {e.detail}")
            return

        if not active_units:
            st.info("No active units in the portfolio.")
        else:
            # Format table
            display_data = []
            for u in active_units:
                display_data.append({
                    "ID": u["id"],
                    "Unit #": u["unit_number"],
                    "Address": u["address"],
                    "Monthly Rent": f"${float(u['monthly_rent']):,.2f}",
                    "Tenant": u["tenant_name"] or "— Vacant —",
                    "Open Tickets": u.get("open_requests_count", 0),
                    "Rent Status": u.get("current_month_rent_status", "N/A"),
                })
            df = pd.DataFrame(display_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("##### 🔍 Unit Details & Actions")
            selected_unit_num = st.selectbox(
                "Select a unit to inspect, edit, or view maintenance history:",
                options=[u["unit_number"] for u in active_units],
                key="active_unit_select"
            )
            selected_unit = next((u for u in active_units if u["unit_number"] == selected_unit_num), None)

            if selected_unit:
                u_col1, u_col2 = st.columns([1, 1])

                with u_col1:
                    st.markdown("###### Edit Unit Details")
                    with st.form(f"edit_unit_{selected_unit['id']}"):
                        new_number = st.text_input("Unit Number", value=selected_unit["unit_number"])
                        new_address = st.text_input("Address", value=selected_unit["address"])
                        new_rent = st.number_input("Monthly Rent ($)", min_value=1.0, value=float(selected_unit["monthly_rent"]), step=50.0)
                        new_tenant = st.text_input("Tenant Name", value=selected_unit["tenant_name"] or "", help="Leave empty if vacant")

                        if st.form_submit_button("Save Changes", type="primary"):
                            try:
                                ApiClient.update_unit(
                                    selected_unit["id"],
                                    {
                                        "unit_number": new_number,
                                        "address": new_address,
                                        "monthly_rent": new_rent,
                                        "tenant_name": new_tenant if new_tenant.strip() else None
                                    }
                                )
                                st.success("Unit updated successfully!")
                                st.rerun()
                            except ApiError as e:
                                st.error(f"Update failed: {e.detail}")

                    # Archive button
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(f"📦 Archive Unit {selected_unit['unit_number']}", help="Removes unit from active portfolio while preserving history."):
                        try:
                            ApiClient.archive_unit(selected_unit["id"])
                            st.success(f"Unit {selected_unit['unit_number']} archived.")
                            st.rerun()
                        except ApiError as e:
                            st.error(f"Archive failed: {e.detail}")

                with u_col2:
                    st.markdown(f"###### 🛠️ Maintenance Requests for Unit {selected_unit['unit_number']}")
                    try:
                        unit_reqs = ApiClient.get_unit_maintenance(selected_unit["id"])
                        if not unit_reqs:
                            st.info("No maintenance requests logged for this unit.")
                        else:
                            for req in unit_reqs:
                                st.markdown(
                                    f"""
                                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <strong>#{req['id']} {req['description'][:40]}</strong>
                                            <div>
                                                <span class="badge badge-{req['priority'].lower()}">{req['priority']}</span>
                                                <span class="badge badge-{req['status'].lower()}">{req['status']}</span>
                                            </div>
                                        </div>
                                        <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.3rem;">
                                            Reported: {req['created_at'][:10]} · Assigned: {len(req['assigned_contractors'])} contractor(s)
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                    except ApiError as e:
                        st.error(f"Could not load maintenance requests: {e.detail}")

    # --- TAB 2: Archived Units ---
    with tab_archived:
        try:
            all_units = ApiClient.get_units(include_archived=True)
            archived = [u for u in all_units if u.get("archived", False)]
        except ApiError as e:
            st.error(f"Error loading archived units: {e.detail}")
            return

        if not archived:
            st.info("No archived units in the repository.")
        else:
            st.markdown("Archived units are excluded from default views, but all rent and maintenance history remains intact.")
            for au in archived:
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="font-size: 1.1rem; color: #334155;">Unit {au['unit_number']}</strong> — <span style="color: #64748b;">{au['address']}</span>
                                    <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">
                                        Last Tenant: {au['tenant_name'] or 'Vacant'} · Historic Rent: ${float(au['monthly_rent']):,.2f}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    c_res, c_spacer = st.columns([1, 4])
                    with c_res:
                        if st.button(f"♻️ Restore Unit {au['unit_number']}", key=f"restore_{au['id']}"):
                            try:
                                ApiClient.restore_unit(au["id"])
                                st.success(f"Unit {au['unit_number']} restored to active portfolio!")
                                st.rerun()
                            except ApiError as e:
                                st.error(f"Restore failed: {e.detail}")

    # --- TAB 3: Add New Unit ---
    with tab_add:
        st.markdown("##### Add Unit to Portfolio")
        with st.form("create_unit_form"):
            add_num = st.text_input("Unit Identifier / Number", placeholder="e.g. 401 or B-12")
            add_addr = st.text_input("Physical Address", placeholder="e.g. 742 Evergreen Terrace, Apt 401")
            add_rent = st.number_input("Monthly Rent ($)", min_value=1.0, value=1500.0, step=50.0)
            add_tenant = st.text_input("Current Tenant Name (optional)", placeholder="e.g. Jane Smith (leave blank if vacant)")
            add_submit = st.form_submit_button("Create Unit", type="primary")

            if add_submit:
                if not add_num or not add_addr or add_rent <= 0:
                    st.error("Please provide valid unit number, address, and positive rent amount.")
                else:
                    try:
                        ApiClient.create_unit(add_num, add_addr, add_rent, add_tenant)
                        st.success(f"Unit {add_num} created successfully!")
                        st.rerun()
                    except ApiError as e:
                        st.error(f"Failed to create unit: {e.detail}")
