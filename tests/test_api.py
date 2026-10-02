import pytest
from fastapi.testclient import TestClient
from backend.api import app

# Create a test client. This will trigger the lifespan event to load the cache, 
# which takes ~30 seconds but ensures real integration behavior.

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

# We need a real account ID from the DB to test with.
# Let's find one by doing a search first.
@pytest.fixture(scope="session")
def valid_account_id(client):
    response = client.get("/api/accounts/search?q=100")

    assert response.status_code == 200
    data = response.json()["data"]
    if data:
        return data[0]["account_id"]
    return "TEST_ACCOUNT_NOT_FOUND"

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_search_accounts(client):
    response = client.get("/api/accounts/search?q=100")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_get_account_summary_valid(client, valid_account_id):
    response = client.get(f"/api/accounts/{valid_account_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "account_id" in data["data"]
    assert "mule_risk_index" in data["data"]

def test_get_account_summary_invalid(client):
    response = client.get("/api/accounts/NON_EXISTENT_ACC_123")
    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"

def test_get_account_transactions(client, valid_account_id):
    response = client.get(f"/api/accounts/{valid_account_id}/transactions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) <= 5

def test_get_risk(client, valid_account_id):
    response = client.get(f"/api/accounts/{valid_account_id}/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "mule_risk_index" in data["data"]

def test_get_trail(client, valid_account_id):
    response = client.get(f"/api/accounts/{valid_account_id}/trail?hops=2")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "nodes" in data["data"]
    assert "edges" in data["data"]

def test_get_trail_invalid_hops(client, valid_account_id):
    # Hops must be between 1 and 4
    response = client.get(f"/api/accounts/{valid_account_id}/trail?hops=5")
    assert response.status_code == 422 # FastAPI validation error

def test_get_timeline(client, valid_account_id):
    response = client.get(f"/api/accounts/{valid_account_id}/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_get_detections(client, valid_account_id):
    response = client.get(f"/api/accounts/{valid_account_id}/detections")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
