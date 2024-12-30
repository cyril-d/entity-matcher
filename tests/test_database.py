import pytest
from app.database import initialize_db, add_schema, get_schema, get_all_schemas

@pytest.fixture
def setup_db():
    initialize_db()

def test_add_and_get_schema(setup_db):
    schema_id = add_schema("Test Schema", {"Entity": {"description": "Sample entity", "fields": ["field1"]}})
    schema = get_schema(schema_id)
    assert schema["name"] == "Test Schema"
    assert schema["entities"]["Entity"]["description"] == "Sample entity"

def test_list_schemas(setup_db):
    add_schema("Schema 1", {})
    add_schema("Schema 2", {})
    schemas = get_all_schemas()
    assert len(schemas) == 2
    assert schemas[0]["name"] == "Schema 1"
    assert schemas[1]["name"] == "Schema 2"
