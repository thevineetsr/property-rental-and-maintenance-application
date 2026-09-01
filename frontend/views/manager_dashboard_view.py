import streamlit as st
import pandas as pd
from frontend.api_client import ApiClient, ApiError


def render_manager_dashboard():
    st.markdown("## 📊 Portfolio Dashboard")
    st.markdown("Real-time portfolio overview, rent performance, and maintenance intelligence.")

    try:
        data = ApiClient.get_manager_dashboard()
    except ApiError as e:
        st.error(f"Failed to load dashboard metrics: {e.detail}")
        return

    # Check for Overdue Alerts Banner
    overdue_count = data.get("overdue_units_count", 0)
    if overdue_count > 0:
        st.markdown(
            f"""
            <div class="alert-banner">
                <div>
                    <strong>⚠️ Rent Attention Required:</strong>
                    {overdue_count} unit(s) have overdue rent this month past the grace period.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 1. Headline KPIs Row 1 (Rent & Units)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Active Units</div>
                <div class="metric-value">{data['total_active_units']}</div>
                <div class="metric-sub">{data['occupied_units']} occupied · {data['vacant_units']} vacant · {data['total_archived_units']} archived</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Expected Monthly Rent</div>
                <div class="metric-value">${float(data['monthly_expected_rent']):,.2f}</div>
                <div class="metric-sub">Active portfolio total</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Rent Collected (This Month)</div>
                <div class="metric-value" style="color: #059669;">${float(data['total_rent_collected_this_month']):,.2f}</div>
                <div class="metric-sub">Recorded payments</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Units Overdue</div>
                <div class="metric-value" style="color: {'#dc2626' if overdue_count > 0 else '#059669'};">{overdue_count}</div>
                <div class="metric-sub">Past 5-day grace period</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # 2. Headline KPIs Row 2 (Maintenance)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Open Maintenance</div>
                <div class="metric-value">{data['open_maintenance_requests']}</div>
                <div class="metric-sub">Reported, Triaged, Scheduled</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">High Priority</div>
                <div class="metric-value" style="color: {'#dc2626' if data['high_priority_requests'] > 0 else '#475569'};">{data['high_priority_requests']}</div>
                <div class="metric-sub">Requires immediate action</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Scheduled</div>
                <div class="metric-value">{data['scheduled_requests']}</div>
                <div class="metric-sub">Contractor on-site / booked</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Resolved This Week</div>
                <div class="metric-value" style="color: #2563eb;">{data['requests_resolved_this_week']}</div>
                <div class="metric-sub">{data['resolved_requests']} all-time resolved</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 3. Trends & Breakdowns
    col_chart, col_status, col_contractors = st.columns([2, 1, 1])

    with col_chart:
        st.markdown("##### 📈 Requests Resolved Per Week (Last 8 Weeks)")
        weekly_data = data.get("weekly_resolved_last_8_weeks", [])
        if weekly_data:
            df_trend = pd.DataFrame(weekly_data)
            df_trend = df_trend.rename(columns={"week_label": "Week", "resolved_count": "Resolved"})
            st.bar_chart(df_trend, x="Week", y="Resolved", color="#2563eb", height=280)
        else:
            st.info("No resolution history recorded yet.")

    with col_status:
        st.markdown("##### 📋 By Status")
        status_data = data.get("requests_by_status", {})
        for st_name, count in status_data.items():
            badge_class = f"badge-{st_name.lower()}"
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9;">
                    <span class="badge {badge_class}">{st_name}</span>
                    <strong style="color: #0f172a; font-size: 1.1rem;">{count}</strong>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_contractors:
        st.markdown("##### 👷 Active per Contractor")
        contractor_data = data.get("requests_by_contractor", {})
        if contractor_data:
            for c_name, count in contractor_data.items():
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9;">
                        <span style="font-size: 0.9rem; color: #334155; font-weight: 500;">{c_name}</span>
                        <span style="background: #eff6ff; color: #1e40af; padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 600;">{count}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No contractors currently registered.")

    st.markdown("---")

    # 4. Unattended Requests Section (>14 days)
    st.markdown("##### ⏳ Unattended Requests (Open > 14 Days)")
    unattended = data.get("unattended_requests", [])
    if unattended:
        st.warning(f"⚠️ {len(unattended)} request(s) have remained in Reported or Triaged status for over 14 days!")
        df_unattended = pd.DataFrame(unattended)
        df_unattended = df_unattended[["id", "unit_number", "priority", "status", "days_open", "description", "created_at"]]
        df_unattended.columns = ["ID", "Unit", "Priority", "Status", "Days Open", "Description", "Created"]
        st.dataframe(df_unattended, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No unattended requests! All open requests were opened within the last 14 days.")
