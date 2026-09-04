import os
import sys

# Ensure repository root is on sys.path so 'frontend' package is resolvable on Streamlit Cloud
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
from frontend.api_client import ApiClient, ApiError
from frontend.views.login_view import render_login_view
from frontend.views.manager_dashboard_view import render_manager_dashboard
from frontend.views.units_view import render_units_view
from frontend.views.rent_view import render_rent_view
from frontend.views.maintenance_view import render_maintenance_view
from frontend.views.contractor_view import render_contractor_view

# Configure Streamlit page
st.set_page_config(
    page_title="PropertyFlow — Rental & Maintenance Management",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    # Session state initialization
    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # Check authentication
    if not st.session_state["token"]:
        render_login_view()
        return

    user = st.session_state["user"]
    user_role = user.get("role", "")

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 0.75rem 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1rem;">
                <h3 style="margin: 0; color: #0f172a;">🏠 PropertyFlow</h3>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.2rem;">Property & Maintenance</div>
            </div>
            <div style="background: #f8fafc; border-radius: 8px; padding: 0.75rem; border: 1px solid #e2e8f0; margin-bottom: 1.5rem;">
                <div style="font-weight: 600; color: #1e293b; font-size: 0.95rem;">{user.get('full_name')}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{user.get('email')}</div>
                <div style="margin-top: 0.4rem;">
                    <span class="badge {'badge-triaged' if user_role == 'PROPERTY_MANAGER' else 'badge-scheduled'}">{user_role.replace('_', ' ')}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Navigation Options based on Role
        if user_role == "PROPERTY_MANAGER":
            # Fetch active rent alerts count for badge in navigation (Requirement 10)
            alert_count = 0
            try:
                alerts = ApiClient.get_rent_alerts()
                alert_count = len(alerts)
            except Exception:
                alert_count = 0

            rent_label = f"💰 Rent Tracking ({alert_count} alert{'s' if alert_count != 1 else ''})" if alert_count > 0 else "💰 Rent Tracking"

            page = st.radio(
                "Navigation",
                options=[
                    "📊 Dashboard",
                    "🏢 Units Portfolio",
                    rent_label,
                    "🛠️ Maintenance Requests"
                ],
                label_visibility="collapsed"
            )
        else:
            page = st.radio(
                "Navigation",
                options=["🔧 My Workspace"],
                label_visibility="collapsed"
            )

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["user"] = None
            st.rerun()

    # Route Page
    if user_role == "PROPERTY_MANAGER":
        if page == "📊 Dashboard":
            render_manager_dashboard()
        elif page == "🏢 Units Portfolio":
            render_units_view()
        elif page.startswith("💰 Rent Tracking"):
            render_rent_view()
        elif page == "🛠️ Maintenance Requests":
            render_maintenance_view()
    else:
        render_contractor_view()


if __name__ == "__main__":
    main()
