from app.matching import match_entities
from app.database import add_schema, initialize_db

def test_match_entities():
    initialize_db()
    source_schema_id = add_schema("Source Schema", {"Customer": {"description": "Customer details", "fields": ["name", "email"]}})
    target_schema_id = add_schema("Target Schema", {"Client": {"description": "Client info", "fields": ["name", "email_address"]}})
    matches = match_entities(source_schema_id, target_schema_id, "Customer")
    assert len(matches) > 0
