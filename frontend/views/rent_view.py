import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from frontend.api_client import ApiClient, ApiError


def render_rent_view():
    st.markdown("## 💰 Rent Tracking & Financials")
    st.markdown("Monitor monthly collections, record payments, bulk-match bank transfers, and resolve alerts.")

    current_month_str = datetime.now(timezone.utc).strftime("%Y-%m")

    # Month selector
    col_sel, col_stats = st.columns([1, 3])
    with col_sel:
        selected_month = st.text_input("Month Covered (YYYY-MM)", value=current_month_str)

    tab_roll, tab_single, tab_bulk, tab_alerts, tab_csv = st.tabs([
        "📋 Rent Roll",
        "💵 Record Single Payment",
        "⚡ Bulk Record Rent",
        "🚨 Rent Alerts",
        "📥 CSV Export"
    ])

    # --- TAB 1: Rent Roll ---
    with tab_roll:
        try:
            roll = ApiClient.get_rent_status(month=selected_month)
        except ApiError as e:
            st.error(f"Failed to load rent roll: {e.detail}")
            return

        if not roll:
            st.info(f"No active units found for month {selected_month}.")
        else:
            total_expected = sum(float(r["monthly_rent"]) for r in roll)
            total_collected = sum(float(r["amount_paid"]) for r in roll)
            total_outstanding = total_expected - total_collected

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Total Expected", f"${total_expected:,.2f}")
            with k2:
                st.metric("Total Collected", f"${total_collected:,.2f}")
            with k3:
                st.metric("Outstanding Balance", f"${max(0.0, total_outstanding):,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)
            table_data = []
            for r in roll:
                table_data.append({
                    "Unit #": r["unit_number"],
                    "Address": r["address"],
                    "Tenant": r["tenant_name"] or "— Vacant —",
                    "Monthly Rent": f"${float(r['monthly_rent']):,.2f}",
                    "Amount Paid": f"${float(r['amount_paid']):,.2f}",
                    "Balance": f"${float(r['balance']):,.2f}",
                    "Status": r["status"],
                    "Alert Active": "⚠️ Overdue" if r["is_alert_active"] else "—"
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # --- TAB 2: Record Single Payment ---
    with tab_single:
        st.markdown("##### Record Rent Payment")
        try:
            units = ApiClient.get_units(include_archived=False)
            unit_options = {f"Unit {u['unit_number']} — {u['tenant_name'] or 'Vacant'}": u["id"] for u in units}
        except ApiError:
            unit_options = {}

        if not unit_options:
            st.info("No units available.")
        else:
            with st.form("single_payment_form"):
                sel_label = st.selectbox("Select Unit", options=list(unit_options.keys()))
                unit_id = unit_options[sel_label]
                # Find matching unit to prefill monthly rent
                matching_unit = next((u for u in units if u["id"] == unit_id), None)
                default_amount = float(matching_unit["monthly_rent"]) if matching_unit else 1000.0

                pay_amount = st.number_input("Payment Amount ($)", min_value=1.0, value=default_amount, step=50.0)
                pay_month = st.text_input("Month Covered (YYYY-MM)", value=selected_month)
                pay_notes = st.text_input("Payment Notes / Reference", placeholder="e.g. Bank Transfer Ref #9812, Check #104")
                pay_submit = st.form_submit_button("Record Payment", type="primary")

                if pay_submit:
                    try:
                        ApiClient.record_payment(unit_id, pay_amount, pay_month, pay_notes)
                        st.success(f"Payment of ${pay_amount:,.2f} recorded for {sel_label} covering {pay_month}!")
                        st.rerun()
                    except ApiError as e:
                        st.error(f"Payment failed: {e.detail}")

    # --- TAB 3: Bulk Record Rent ---
    with tab_bulk:
        st.markdown("##### ⚡ Bulk Rent Processing")
        st.markdown(
            "Batch-record monthly payments received via bank transfer or checks in a single transaction. "
            "Each line will be classified as **matched** (equals rent), **underpaid**, **overpaid**, or **unmatched**."
        )

        sample_text = "101, 1500.00\n102, 1200.00\n201, 1700.00\n999, 1000.00"
        bulk_input = st.text_area(
            "Enter lines in format: `Unit_Identifier, Amount` (one per line):",
            value=sample_text,
            height=130
        )
        bulk_month = st.text_input("Month to apply payments to:", value=selected_month, key="bulk_month_input")

        if st.button("Process Bulk Payments", type="primary"):
            lines = bulk_input.strip().split("\n")
            payments_list = []
            parse_errors = []

            for idx, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    parse_errors.append(f"Line {idx}: Must contain unit identifier and amount separated by comma.")
                    continue
                ident, amt_str = parts[0].strip(), parts[1].strip()
                try:
                    amt = float(amt_str)
                    if amt <= 0:
                        parse_errors.append(f"Line {idx}: Amount must be positive.")
                        continue
                    payments_list.append({"unit_identifier": ident, "amount": amt})
                except ValueError:
                    parse_errors.append(f"Line {idx}: '{amt_str}' is not a valid number.")

            if parse_errors:
                for err in parse_errors:
                    st.error(err)
            elif not payments_list:
                st.warning("No valid payment rows to process.")
            else:
                try:
                    res = ApiClient.bulk_record_rent(bulk_month, payments_list)
                    st.success(f"Processed {res['total_rows']} rows! Matched: {res['matched_count']} · Underpaid: {res['underpaid_count']} · Overpaid: {res['overpaid_count']} · Unmatched: {res['unmatched_count']}")

                    # Display classification report
                    results_data = []
                    for row in res["results"]:
                        results_data.append({
                            "Identifier": row["unit_identifier"],
                            "Unit #": row["unit_number"] or "—",
                            "Tenant": row["tenant_name"] or "—",
                            "Monthly Rent": f"${float(row['monthly_rent']):,.2f}" if row["monthly_rent"] else "—",
                            "Amount Received": f"${float(row['amount_received']):,.2f}",
                            "Classification": row["classification"].upper(),
                            "Notes": row["notes"]
                        })
                    st.dataframe(pd.DataFrame(results_data), use_container_width=True, hide_index=True)
                except ApiError as e:
                    st.error(f"Bulk processing error: {e.detail}")

    # --- TAB 4: Rent Alerts ---
    with tab_alerts:
        st.markdown("##### 🚨 Overdue Rent Alerts")
        st.markdown(
            "Units whose rent has not been matched by a full payment once the **5-day grace period** passes appear here. "
            "Dismissing an alert suppresses it for this month only; if unpaid in a subsequent month, it will return."
        )

        try:
            alerts = ApiClient.get_rent_alerts(month=selected_month)
        except ApiError as e:
            st.error(f"Failed to load alerts: {e.detail}")
            return

        if not alerts:
            st.success(f"🎉 No active rent alerts for {selected_month}!")
        else:
            for alert in alerts:
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: #991b1b; font-size: 1.1rem;">Unit {alert['unit_number']}</strong>
                                    <span style="color: #7f1d1d;"> — Tenant: {alert['tenant_name'] or 'Vacant'}</span>
                                    <div style="font-size: 0.85rem; color: #b91c1c; margin-top: 0.25rem;">
                                        Monthly Rent: ${float(alert['monthly_rent']):,.2f} · Paid: ${float(alert['amount_paid']):,.2f} · <strong>Remaining Balance: ${float(alert['balance']):,.2f}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    c_btn, _ = st.columns([1, 4])
                    with c_btn:
                        if st.button(f"Dismiss Alert for Unit {alert['unit_number']}", key=f"dismiss_{alert['unit_id']}"):
                            try:
                                ApiClient.dismiss_rent_alert(alert["unit_id"], alert["month_covered"])
                                st.success(f"Alert dismissed for Unit {alert['unit_number']} for {selected_month}.")
                                st.rerun()
                            except ApiError as e:
                                st.error(f"Failed to dismiss: {e.detail}")

    # --- TAB 5: CSV Export ---
    with tab_csv:
        st.markdown("##### 📥 Export Rent Roll CSV")
        st.markdown("Download the full rent roll containing units, tenants, monthly rent, and current payment status.")

        try:
            csv_data = ApiClient.get_rent_roll_csv(month=selected_month)
            st.download_button(
                label=f"⬇️ Download Rent Roll CSV ({selected_month})",
                data=csv_data,
                file_name=f"rent_roll_{selected_month}.csv",
                mime="text/csv",
                type="primary"
            )
            with st.expander("Preview CSV Content"):
                st.code(csv_data, language="csv")
        except ApiError as e:
            st.error(f"Failed to generate CSV: {e.detail}")
