from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _auth_headers(
    email: str = "user@example.com",
    password: str = "example-password",
) -> dict[str, str]:
    client.post(
        "/users",
        json={"email": email, "password": password},
    )
    login_response = client.post(
        "/token",
        data={"username": email, "password": password},
    )
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def test_create_application_rejects_missing_token():
    response = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend Engineer"},
    )
    assert response.status_code == 401


def test_read_applications_rejects_missing_token():
    response = client.get("/applications")
    assert response.status_code == 401


def test_read_application_rejects_missing_token():
    response = client.get("/applications/1")
    assert response.status_code == 401


def test_update_application_rejects_missing_token():
    response = client.put(
        "/applications/1",
        json={"company": "Acme", "position": "Backend Engineer"},
    )
    assert response.status_code == 401


def test_delete_application_rejects_missing_token():
    response = client.delete("/applications/1")
    assert response.status_code == 401


def test_create_application_with_all_fields():
    headers = _auth_headers()
    payload = {
        "company": "Acme",
        "position": "Backend Engineer",
        "status": "applied",
        "applied_at": "2026-09-14",
        "notes": "Referred by a friend",
    }

    response = client.post("/applications", json=payload, headers=headers)

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["id"] > 0
    assert response_data["company"] == payload["company"]
    assert response_data["position"] == payload["position"]
    assert response_data["status"] == payload["status"]
    assert response_data["applied_at"] == payload["applied_at"]
    assert response_data["notes"] == payload["notes"]


def test_create_application_defaults_status_to_saved():
    headers = _auth_headers()
    payload = {"company": "Acme", "position": "Backend Engineer"}

    response = client.post("/applications", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["status"] == "saved"
    assert response.json()["applied_at"] is None
    assert response.json()["notes"] is None


def test_create_application_rejects_missing_company():
    headers = _auth_headers()
    payload = {"position": "Backend Engineer"}

    response = client.post("/applications", json=payload, headers=headers)

    assert response.status_code == 422


def test_create_application_rejects_missing_position():
    headers = _auth_headers()
    payload = {"company": "Acme"}

    response = client.post("/applications", json=payload, headers=headers)

    assert response.status_code == 422


def test_create_application_rejects_invalid_status():
    headers = _auth_headers()
    payload = {
        "company": "Acme",
        "position": "Backend Engineer",
        "status": "not-a-real-status",
    }

    response = client.post("/applications", json=payload, headers=headers)

    assert response.status_code == 422


def test_read_own_application():
    headers = _auth_headers()
    payload = {"company": "Acme", "position": "Backend Engineer"}
    created = client.post("/applications", json=payload, headers=headers).json()

    response = client.get(f"/applications/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json() == created


def test_read_missing_application_returns_404():
    headers = _auth_headers()

    response = client.get("/applications/999", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_read_other_users_application_returns_404():
    owner_headers = _auth_headers(email="owner@example.com")
    other_headers = _auth_headers(email="other@example.com")
    created = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend Engineer"},
        headers=owner_headers,
    ).json()

    response = client.get(
        f"/applications/{created['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_read_applications_lists_only_own_applications():
    owner_headers = _auth_headers(email="owner@example.com")
    other_headers = _auth_headers(email="other@example.com")
    client.post(
        "/applications",
        json={"company": "Owner Co", "position": "Backend Engineer"},
        headers=owner_headers,
    )
    client.post(
        "/applications",
        json={"company": "Other Co", "position": "Backend Engineer"},
        headers=other_headers,
    )

    response = client.get("/applications", headers=owner_headers)

    assert response.status_code == 200
    companies = [application["company"] for application in response.json()]
    assert companies == ["Owner Co"]


def test_read_applications_with_offset_and_limit():
    headers = _auth_headers()
    for company in ["First Co", "Second Co", "Third Co"]:
        client.post(
            "/applications",
            json={"company": company, "position": "Backend Engineer"},
            headers=headers,
        )

    response = client.get(
        "/applications",
        params={"offset": 1, "limit": 1},
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["company"] == "Second Co"


def test_update_own_application():
    headers = _auth_headers()
    created = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend Engineer"},
        headers=headers,
    ).json()

    update_payload = {
        "company": "Acme",
        "position": "Senior Backend Engineer",
        "status": "interviewing",
        "applied_at": "2026-09-10",
        "notes": "Onsite scheduled",
    }
    response = client.put(
        f"/applications/{created['id']}",
        json=update_payload,
        headers=headers,
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == created["id"]
    assert response_data["position"] == update_payload["position"]
    assert response_data["status"] == update_payload["status"]
    assert response_data["applied_at"] == update_payload["applied_at"]
    assert response_data["notes"] == update_payload["notes"]


def test_update_missing_application_returns_404():
    headers = _auth_headers()
    update_payload = {"company": "Acme", "position": "Backend Engineer"}

    response = client.put(
        "/applications/999",
        json=update_payload,
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_update_other_users_application_returns_404():
    owner_headers = _auth_headers(email="owner@example.com")
    other_headers = _auth_headers(email="other@example.com")
    created = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend Engineer"},
        headers=owner_headers,
    ).json()

    response = client.put(
        f"/applications/{created['id']}",
        json={"company": "Hijacked", "position": "Backend Engineer"},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_delete_own_application():
    headers = _auth_headers()
    created = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend Engineer"},
        headers=headers,
    ).json()

    response = client.delete(f"/applications/{created['id']}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""

    check_response = client.get(f"/applications/{created['id']}", headers=headers)
    assert check_response.status_code == 404


def test_delete_missing_application_returns_404():
    headers = _auth_headers()

    response = client.delete("/applications/999", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_delete_other_users_application_returns_404():
    owner_headers = _auth_headers(email="owner@example.com")
    other_headers = _auth_headers(email="other@example.com")
    created = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend Engineer"},
        headers=owner_headers,
    ).json()

    response = client.delete(
        f"/applications/{created['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}

    check_response = client.get(
        f"/applications/{created['id']}",
        headers=owner_headers,
    )
    assert check_response.status_code == 200


def _create_many_applications(headers) -> list[dict]:
    """创建 5 条投递记录用于分页/筛选/排序测试。"""
    payloads = [
        {"company": "Google", "position": "SDE", "status": "applied", "applied_at": "2026-09-15"},
        {"company": "Acme Inc", "position": "Backend", "status": "interviewing", "applied_at": "2026-09-10"},
        {"company": "Amazon", "position": "SDE", "status": "rejected", "applied_at": "2026-09-01"},
        {"company": "Acme Corp", "position": "Frontend", "status": "applied", "applied_at": "2026-09-05"},
        {"company": "StartupX", "position": "ML Engineer", "status": "saved", "applied_at": None},
    ]
    created = []
    for p in payloads:
        resp = client.post(
            "/applications",
            json=p,
            headers=headers,
        )
        assert resp.status_code == 201
        created.append(resp.json())
    return created


def test_filter_by_status():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"status": "applied"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(a["status"] == "applied" for a in data)


def test_filter_by_company_partial_match():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"company": "acme"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("acme" in a["company"].lower() for a in data)


def test_filter_by_company_case_insensitive():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"company": "ACME"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filter_company_and_status():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"company": "acme", "status": "applied"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["company"] == "Acme Corp"


def test_filter_by_status_no_match():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"status": "offer"},
        headers=headers
    )

    assert response.status_code == 200
    assert response.json() == []


def test_sort_by_applied_at_desc():
    headers = _auth_headers()
    apps = _create_many_applications(headers)

    response = client.get("/applications", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data[0]["company"] == "Google"  # 2026-09-15, newest first
    assert data[-1]["company"] == "StartupX"  # NULL applied_at, last


def test_sort_by_applied_at_asc():
    headers = _auth_headers()
    apps = _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"sort": "applied_at"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data[0]["company"] == "Amazon"  # 2026-09-01, oldest first
    assert data[-1]["company"] == "StartupX"  # NULL applied_at, last


def test_sort_by_company_asc():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"sort": "company"},
        headers=headers,
    )

    assert response.status_code == 200
    companies = [a["company"] for a in response.json()]
    assert companies == sorted(companies)


def test_sort_by_status_desc_company_asc():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"sort": "-status,company"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    for i in range(len(data) - 1):
        if data[i]["status"] == data[i + 1]["status"]:
            assert data[i]["company"] <= data[i + 1]["company"]


def test_sort_invalid_field_returns_422():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"sort": "salary"},
        headers=headers,
    )

    assert response.status_code == 422


def test_sort_invalid_format_returns_422():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get(
        "/applications",
        params={"sort": "sql--"},
        headers=headers,
    )

    assert response.status_code == 422


def test_list_default_sort_without_params():
    headers = _auth_headers()
    _create_many_applications(headers)

    response = client.get("/applications", headers=headers)

    assert response.status_code == 200
    data = response.json()
    ids = [a["id"] for a in data]
    # Default sort: -applied_at,id. All non-NULL applied_at sorted desc,
    # ties broken by id asc, NULLs at the end
    assert data[-1]["applied_at"] is None
