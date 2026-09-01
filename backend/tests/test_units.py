def test_manager_can_create_unit(client, manager_token):
    res = client.post(
        "/api/units",
        json={
            "unit_number": "U-501",
            "address": "500 Main St, Apt 501",
            "monthly_rent": 1350.00,
            "tenant_name": "Test Tenant"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["unit_number"] == "U-501"
    assert float(data["monthly_rent"]) == 1350.00
    assert data["archived"] is False


def test_contractor_cannot_create_unit(client, contractor1_token):
    res = client.post(
        "/api/units",
        json={
            "unit_number": "U-502",
            "address": "500 Main St, Apt 502",
            "monthly_rent": 1400.00,
            "tenant_name": "Test Tenant"
        },
        headers={"Authorization": f"Bearer {contractor1_token}"}
    )
    assert res.status_code == 403
    assert "Access forbidden" in res.json()["detail"]


def test_manager_can_edit_unit(client, manager_token, test_unit):
    res = client.patch(
        f"/api/units/{test_unit.id}",
        json={"tenant_name": "Updated Tenant Name", "monthly_rent": 1250.00},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tenant_name"] == "Updated Tenant Name"
    assert float(data["monthly_rent"]) == 1250.00


def test_contractor_cannot_edit_unit(client, contractor1_token, test_unit):
    res = client.patch(
        f"/api/units/{test_unit.id}",
        json={"tenant_name": "Hacked Tenant"},
        headers={"Authorization": f"Bearer {contractor1_token}"}
    )
    assert res.status_code == 403


def test_archive_and_restore_unit(client, manager_token, test_unit):
    # Archive unit
    res = client.post(
        f"/api/units/{test_unit.id}/archive",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    assert res.json()["archived"] is True

    # Default list excludes archived unit
    res = client.get("/api/units", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    unit_ids = [u["id"] for u in res.json()]
    assert test_unit.id not in unit_ids

    # Query with include_archived=True includes it
    res = client.get("/api/units?include_archived=true", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    unit_ids = [u["id"] for u in res.json()]
    assert test_unit.id in unit_ids

    # Restore unit
    res = client.post(
        f"/api/units/{test_unit.id}/restore",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 200
    assert res.json()["archived"] is False

    # Appears in default list again
    res = client.get("/api/units", headers={"Authorization": f"Bearer {manager_token}"})
    unit_ids = [u["id"] for u in res.json()]
    assert test_unit.id in unit_ids


def test_contractor_units_rent_masked(client, contractor1_token, test_unit):
    res = client.get("/api/units", headers={"Authorization": f"Bearer {contractor1_token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    # Strictly ensure rent data is masked for contractors
    for u in data:
        assert u["monthly_rent"] is None
        assert u["current_month_rent_status"] == "HIDDEN"

