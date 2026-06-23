import sys
import os
import uuid
from fastapi.testclient import TestClient

# Ensure backend directory is in the python path for importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

def test_health_check():
    """
    Asserts GET /health reports healthy status and 200 OK.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_pricing_rule_75028():
    """
    Asserts ZIP 75028 applies custom pricing rule ($1,499.00) with a valid correlation ID.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": "75028"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["zip_code"] == "75028"
    assert data["price"] == 1499.00
    assert data["formatted_price"] == "$1,499.00"
    assert data["is_custom"] is True

def test_pricing_rule_10001():
    """
    Asserts ZIP 10001 applies custom pricing rule ($1,699.00) with a valid correlation ID.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": "10001"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["price"] == 1699.00
    assert data["formatted_price"] == "$1,699.00"
    assert data["is_custom"] is True

def test_pricing_rule_90210():
    """
    Asserts ZIP 90210 applies custom pricing rule ($1,799.00) with a valid correlation ID.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["price"] == 1799.00
    assert data["formatted_price"] == "$1,799.00"
    assert data["is_custom"] is True

def test_pricing_fallback_unmapped_zip():
    """
    Asserts an unmapped ZIP code falls back to storefront defaults gracefully.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": "44101"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["price"] is None
    assert data["formatted_price"] is None
    assert data["is_custom"] is False

def test_invalid_zip_formats():
    """
    Asserts invalid zip codes (letters, spaces, wrong lengths) are rejected with a 422 error.
    """
    req_id = str(uuid.uuid4())
    invalid_zips = ["abcde", "1234", "123456", "9021o", " 90210"]
    for zip_code in invalid_zips:
        payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": zip_code}
        response = client.post("/api/v1/pricing/calculate", json=payload)
        assert response.status_code == 422

def test_invalid_product_id():
    """
    Asserts invalid product IDs are rejected with a 422 error.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": -1, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 422

def test_invalid_or_missing_request_id():
    """
    Asserts missing or malformed request correlation UUIDs are rejected with a 422 error.
    """
    # 1. Missing request_id
    payload = {"product_id": 8729384910283, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 422

    # 2. Malformed request_id (not a UUID)
    payload = {"request_id": "not-a-uuid", "product_id": 8729384910283, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 422
