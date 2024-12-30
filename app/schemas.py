import json

# In-memory database for schemas
SCHEMAS_DB = {}

def add_schema(schema_name, schema_data):
    """Adds a schema to the in-memory database."""
    if schema_name in SCHEMAS_DB:
        raise ValueError("Schema with this name already exists.")
    SCHEMAS_DB[schema_name] = schema_data

def get_all_schemas():
    """Returns all schemas."""
    return [{"name": name, "entities": list(data.keys())} for name, data in SCHEMAS_DB.items()]

def get_schema(schema_name):
    """Fetches a schema by name."""
    return SCHEMAS_DB.get(schema_name)

def get_entity(schema_name, entity_name):
    """Fetches an entity by name within a schema."""
    schema = SCHEMAS_DB.get(schema_name)
    if not schema:
        return None
    return schema.get(entity_name)
