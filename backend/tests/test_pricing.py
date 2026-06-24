import sys
import os
import uuid
import hmac
import hashlib
import time
from fastapi.testclient import TestClient

# Ensure backend directory is in the python path for importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import settings

client = TestClient(app)

# Configure test secret globally for signature verification
settings.SHOPIFY_API_SECRET = "test_secret"

def get_signed_query_params(extra_params: dict = None) -> dict:
    params = {
        "shop": "test-store.myshopify.com",
        "path_prefix": "/apps/zip-pricing",
        "timestamp": str(int(time.time())),
        "logged_in_customer_id": ""
    }
    if extra_params:
        params.update(extra_params)
        
    sorted_keys = sorted(params.keys())
    data_parts = []
    for key in sorted_keys:
        value = params[key]
        if isinstance(value, list):
            data_parts.append(f"{key}={','.join(value)}")
        else:
            data_parts.append(f"{key}={value}")
            
    data_string = "".join(data_parts)
    signature = hmac.new(b"test_secret", data_string.encode("utf-8"), hashlib.sha256).hexdigest()
    params["signature"] = signature
    return params

def test_health_check():
    """
    Asserts GET /health reports healthy status and 200 OK.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_verify_proxy_success():
    """
    Asserts GET /api/v1/pricing/verify-proxy succeeds with a valid Shopify signature.
    """
    params = get_signed_query_params()
    response = client.get("/api/v1/pricing/verify-proxy", params=params)
    assert response.status_code == 200
    assert response.json() == {"status": "verified"}

def test_verify_proxy_invalid_signature():
    """
    Asserts GET /api/v1/pricing/verify-proxy returns 401 with an invalid signature.
    """
    params = {
        "shop": "test-store.myshopify.com",
        "path_prefix": "/apps/zip-pricing",
        "timestamp": "1234567890",
        "signature": "invalid_sig"
    }
    response = client.get("/api/v1/pricing/verify-proxy", params=params)
    assert response.status_code == 401

def test_pricing_calculate_unsigned_fails():
    """
    Asserts POST /api/v1/pricing/calculate rejects direct unsigned requests with 401.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": "75028"}
    response = client.post("/api/v1/pricing/calculate", json=payload)
    assert response.status_code == 401

def test_pricing_rule_75028():
    """
    Asserts ZIP 75028 applies custom pricing rule ($1,499.00) with a valid correlation ID.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": 8729384910283, "zip_code": "75028"}
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
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
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
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
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
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
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
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
        response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
        assert response.status_code == 422

def test_invalid_product_id():
    """
    Asserts invalid product IDs are rejected with a 422 error.
    """
    req_id = str(uuid.uuid4())
    payload = {"request_id": req_id, "product_id": -1, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
    assert response.status_code == 422

def test_invalid_or_missing_request_id():
    """
    Asserts missing or malformed request correlation UUIDs are rejected with a 422 error.
    """
    # 1. Missing request_id
    payload = {"product_id": 8729384910283, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
    assert response.status_code == 422

    # 2. Malformed request_id (not a UUID)
    payload = {"request_id": "not-a-uuid", "product_id": 8729384910283, "zip_code": "90210"}
    response = client.post("/api/v1/pricing/calculate", params=get_signed_query_params(), json=payload)
    assert response.status_code == 422
