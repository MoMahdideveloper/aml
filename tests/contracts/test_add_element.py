import requests
import uuid

BASE_URL = "http://localhost:5678/webhook"

def test_add_element():
    """Test adding a non-functional element to a review."""
    review_id = str(uuid.uuid4())
    url = f"{BASE_URL}/reviews/{review_id}/elements"
    payload = {
        "page": "Dashboard",
        "section": "navigation",
        "element_type": "button",
        "element_description": "Refresh button",
        "expected_behavior": "Page should refresh",
        "actual_behavior": "Nothing happens",
        "severity": "high"
    }

    response = requests.post(url, json=payload, timeout=5)

    # We expect the test to fail because the endpoint is not implemented
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    # Additionally, we would check the response schema
    # element = response.json()
    # assert "id" in element
    # assert isinstance(element["id"], str)
    # ... etc.

if __name__ == "__main__":
    test_add_element()