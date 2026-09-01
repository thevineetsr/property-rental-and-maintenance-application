def test_manager_record_payment(client, manager_token, test_unit):
    res = client.post(
        "/api/rent/payments",
        json={
            "unit_id": test_unit.id,
            "amount": 1200.00,
            "month_covered": "2026-09",
            "notes": "Test payment in full"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["unit_id"] == test_unit.id
    assert float(data["amount"]) == 1200.00
    assert data["month_covered"] == "2026-09"


def test_contractor_cannot_record_payment(client, contractor1_token, test_unit):
    res = client.post(
        "/api/rent/payments",
        json={
            "unit_id": test_unit.id,
            "amount": 1200.00,
            "month_covered": "2026-09"
        },
        headers={"Authorization": f"Bearer {contractor1_token}"}
    )
    assert res.status_code == 403


def test_contractor_cannot_access_rent_status(client, contractor1_token):
    res = client.get("/api/rent/status", headers={"Authorization": f"Bearer {contractor1_token}"})
    assert res.status_code == 403


def test_rent_roll_csv_download(client, manager_token, test_unit):
    res = client.get("/api/rent/roll/csv?month=2026-09", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    content = res.text
    assert "Unit Number,Address,Tenant Name,Monthly Rent" in content
    assert test_unit.unit_number in content


def test_dismiss_rent_alert(client, manager_token, test_unit):
    # Check alerts
    res = client.get("/api/rent/alerts?month=2026-01", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200

    # Dismiss alert for unit
    res = client.post(
        f"/api/rent/alerts/{test_unit.id}/dismiss",
        json={"month_covered": "2026-01"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200

    # Now verify it is not in alerts for that month
    res = client.get("/api/rent/alerts?month=2026-01", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    alert_unit_ids = [a["unit_id"] for a in res.json()]
    assert test_unit.id not in alert_unit_ids
