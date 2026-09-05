import streamlit as st
from frontend.api_client import ApiClient, ApiError


def render_login_view():
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="color: #0f172a; margin-bottom: 0.25rem;">🏠 PropertyFlow</h1>
            <p style="color: #64748b; font-size: 1.1rem;">Enterprise Property Rental & Maintenance Management</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔐 Sign In", "📝 Create Account"])

        with tab_login:
            st.markdown("##### Quick Demo Access (1-Click Fill)")
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                if st.button("👑 Admin / Manager\n(admin@property.com)", use_container_width=True):
                    _do_login("admin@property.com", "admin123")
            with row1_col2:
                if st.button("🏢 Manager (Sarah)\n(manager@property.com)", use_container_width=True):
                    _do_login("manager@property.com", "Manager123!")

            row2_col1, row2_col2, row2_col3 = st.columns(3)
            with row2_col1:
                if st.button("🔧 Plumber (Bob)", use_container_width=True):
                    _do_login("bob@contractor.com", "Contractor123!")
            with row2_col2:
                if st.button("⚡ Electrician (Alice)", use_container_width=True):
                    _do_login("alice@contractor.com", "Contractor123!")
            with row2_col3:
                if st.button("🔨 Contractor (Mridul)", use_container_width=True):
                    _do_login("mridul@contractor.com", "mridul123")

            st.markdown("---")
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="name@domain.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        _do_login(email, password)

        with tab_register:
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="e.g. John Smith")
                reg_email = st.text_input("Email Address", placeholder="e.g. john@property.com")
                reg_password = st.text_input("Password", type="password", placeholder="At least 6 characters")
                reg_role = st.selectbox(
                    "System Role",
                    options=["PROPERTY_MANAGER", "MAINTENANCE_CONTRACTOR"],
                    format_func=lambda x: "Property Manager (Full Portfolio Access)" if x == "PROPERTY_MANAGER" else "Maintenance Contractor (Assigned Tickets Only)"
                )
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

                if reg_submitted:
                    if not reg_name or not reg_email or not reg_password:
                        st.error("All fields are required.")
                    else:
                        try:
                            ApiClient.register(reg_email, reg_password, reg_name, reg_role)
                            st.success("Account created successfully! Please sign in above.")
                        except ApiError as e:
                            st.error(f"Registration failed: {e.detail}")


def _do_login(email: str, password: str):
    try:
        data = ApiClient.login(email, password)
        st.session_state["token"] = data["access_token"]
        st.session_state["user"] = data["user"]
        st.success(f"Welcome back, {data['user']['full_name']}!")
        st.rerun()
    except ApiError as e:
        st.error(f"Sign in failed: {e.detail}")
