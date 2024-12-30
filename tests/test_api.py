from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_schema():
    response = client.post("/upload-schema/", json={
        "name": "Schema A",
        "entities": {
            "Customer": {
                "description": "Details about the customer",
                "fields": ["name", "email"]
            }
        }
    })
    assert response.status_code == 200
    assert "Schema 'Schema A' uploaded successfully!" in response.json()["message"]

def test_list_schemas():
    response = client.get("/schemas/")
    assert response.status_code == 200
    assert len(response.json()["schemas"]) > 0

def test_match_entities():
    # Upload schemas
    client.post("/upload-schema/", json={"name": "Schema A", "entities": {"Customer": {"description": "Customer details"}}})
    client.post("/upload-schema/", json={"name": "Schema B", "entities": {"Client": {"description": "Client details"}}})
    
    # Match entities
    response = client.post("/match-entities/", json={"source_schema_id": 1, "target_schema_id": 2, "entity_name": "Customer"})
    assert response.status_code == 200
    assert "matches" in response.json()
