"""Self-check for per-user AI key isolation and resolution."""
from app import ai


def test_ai_resolution():
    # 1. Client-provided Anthropic credentials
    prov, key, model, url = ai.resolve(
        client_ai={"provider": "anthropic", "api_key": "sk-ant-user1", "model": "claude-3-5-sonnet-20241022"}
    )
    assert prov == "anthropic"
    assert key == "sk-ant-user1"
    assert model == "claude-3-5-sonnet-20241022"
    assert url == ""

    # 2. Client-provided Codecraft credentials with base_url
    prov, key, model, url = ai.resolve(
        client_ai={"provider": "codecraft", "api_key": "cc-key-user2", "model": "claude-sonnet-5", "base_url": "https://api.codecraft.org/v1/"}
    )
    assert prov == "codecraft"
    assert key == "cc-key-user2"
    assert model == "claude-sonnet-5"
    assert url == "https://api.codecraft.org/v1"

    # 3. Missing API key raises AIError
    try:
        ai.resolve("anthropic", client_ai={"api_key": "", "model": "claude-3-5-sonnet-20241022"})
        assert False, "Should have raised AIError for missing key"
    except ai.AIError as e:
        assert "No API key" in str(e)

    # 4. Codecraft without base_url raises AIError
    try:
        ai.resolve("codecraft", client_ai={"api_key": "cc-key", "model": "m", "base_url": ""})
        assert False, "Should have raised AIError for missing base URL"
    except ai.AIError as e:
        assert "needs a base URL" in str(e)

    # 5. public_settings never leaks secret keys
    pub = ai.public_settings()
    assert "catalog" in pub
    assert "api_key" not in pub
    for p_info in pub["catalog"].values():
        assert "api_key" not in p_info

    print("Unit resolution self-checks passed!")


def test_fastapi_endpoints():
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. GET /api/ai/settings returns catalog without any exposed keys
    resp = client.get("/api/ai/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "catalog" in data
    assert "api_key" not in data

    # 2. POST /api/ai/test without key returns 400 with helpful error
    resp = client.post("/api/ai/test", json={"provider": "anthropic", "api_key": ""})
    assert resp.status_code == 400
    assert "No API key" in resp.json()["detail"]

    # 3. POST /api/ai/models without key returns 400 with helpful error
    resp = client.post("/api/ai/models", json={"provider": "openai", "api_key": ""})
    assert resp.status_code == 400
    assert "Enter your API key" in resp.json()["detail"]

    print("API endpoint self-checks passed!")


def test_user_isolation():
    from starlette.testclient import TestClient
    from app.main import app
    from app import db

    client = TestClient(app)

    uid_a = "user_test_alice_123"
    uid_b = "user_test_bob_456"

    # 1. Alice sets her profile
    resp_a = client.put(
        "/api/profile",
        json={"name": "Alice Developer", "skills": ["Python", "Django", "FastAPI"], "years_experience": 5},
        headers={"x-user-id": uid_a},
    )
    assert resp_a.status_code == 200
    p_a = resp_a.json()
    assert p_a["name"] == "Alice Developer"
    assert "Python" in p_a["skills"]

    # 2. Bob fetches his profile - should be fresh/empty and NOT have Alice's data
    resp_b = client.get("/api/profile", headers={"x-user-id": uid_b})
    assert resp_b.status_code == 200
    p_b = resp_b.json()
    assert p_b["name"] != "Alice Developer"
    assert "Python" not in p_b.get("skills", [])

    # 3. Bob sets his profile
    client.put(
        "/api/profile",
        json={"name": "Bob Analyst", "skills": ["SQL", "Tableau"], "years_experience": 2},
        headers={"x-user-id": uid_b},
    )

    # 4. Check Alice's profile again - remains Alice Developer
    resp_a2 = client.get("/api/profile", headers={"x-user-id": uid_a})
    assert resp_a2.json()["name"] == "Alice Developer"

    # 5. Job status isolation: Alice saves a job (e.g. job_id = 1)
    # Ensure there is at least one job in the database for the test
    first_job = db.q("SELECT id FROM jobs LIMIT 1", one=True)
    if first_job:
        jid = first_job["id"]
        # Alice saves it
        s_a = client.post(f"/api/jobs/{jid}/status", json={"status": "saved"}, headers={"x-user-id": uid_a})
        assert s_a.status_code == 200

        # Check job detail for Alice -> saved
        j_a = client.get(f"/api/jobs/{jid}", headers={"x-user-id": uid_a}).json()
        assert j_a["status"] == "saved"

        # Check job detail for Bob -> new (NOT saved for Bob!)
        j_b = client.get(f"/api/jobs/{jid}", headers={"x-user-id": uid_b}).json()
        assert j_b["status"] == "new"

    # 6. Apply profile isolation: Alice sets email
    client.put("/api/apply/profile", json={"first_name": "Alice", "email": "alice@test.com"}, headers={"x-user-id": uid_a})
    ap_b = client.get("/api/apply/profile", headers={"x-user-id": uid_b}).json()["profile"]
    assert ap_b.get("email") != "alice@test.com"

    print("User candidate isolation self-checks passed!")


if __name__ == "__main__":
    test_ai_resolution()
    test_fastapi_endpoints()
    test_user_isolation()
