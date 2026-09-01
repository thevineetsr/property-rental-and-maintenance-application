def test_immutable_timeline_recording(client, manager_token, test_users, test_unit):
    # 1. Create request
    res = client.post(
        "/api/maintenance",
        json={"unit_id": test_unit.id, "description": "Broken window lock", "priority": "MEDIUM"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    req_id = res.json()["id"]

    # 2. Advance to TRIAGED
    client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "TRIAGED", "note": "Verified window damage"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )

    # 3. Assign Bob
    client.post(
        f"/api/maintenance/{req_id}/contractors",
        json={"contractor_ids": [test_users["contractor1"].id]},
        headers={"Authorization": f"Bearer {manager_token}"}
    )

    # 4. Advance to SCHEDULED
    client.patch(
        f"/api/maintenance/{req_id}/status",
        json={"status": "SCHEDULED"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )

    # 5. Add note
    client.post(
        f"/api/maintenance/{req_id}/notes",
        json={"note": "Replacement sash lock received"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )

    # 6. Fetch request and verify timeline
    res = client.get(f"/api/maintenance/{req_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert res.status_code == 200
    timeline = res.json()["timeline_events"]

    event_types = [e["event_type"] for e in timeline]
    assert "CREATED" in event_types
    assert "STATUS_CHANGED" in event_types
    assert "CONTRACTOR_ASSIGNED" in event_types
    assert "NOTE_ADDED" in event_types

    # Ensure events are chronologically ordered
    timestamps = [e["created_at"] for e in timeline]
    assert timestamps == sorted(timestamps)
