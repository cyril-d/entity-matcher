from flask import Flask, request, jsonify
from flask_cors import CORS
from app.match import match_fields
from app.database import db, Schema, Entity, Field, get_matching_data_from_db, get_schema_entities, store_matching_data_in_db

app = Flask(__name__)
CORS(app)  # Not working.
# CORS(app, resources={r"/schemas/*": {"origins": "http://localhost:3000"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schemas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

def generateResponse(json, statusCode):
    response = jsonify(json)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.status_code = statusCode
    print(response)
    return response;

@app.route('/api/schema', methods=['POST'])
def api_insert_or_update_schema():
    """API to insert or update a schema."""
    data = request.get_json()

    schema_name = data.get('schema_name')
    schema_description = data.get('schema_description')

    if not schema_name:
        return jsonify({"error": "Schema name is required."}), 400

    try:
        schema = insert_or_update_schema(
            schema_name=schema_name,
            schema_description=schema_description
        )
        return generateResponse({
            "message": "Schema inserted/updated successfully.",
            "schema": {
                "id": schema.id,
                "name": schema.name,
                "description": schema.description
            }
        }, 201)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

@app.route('/api/entity', methods=['POST'])
def api_insert_or_update_entity():
    """API to insert or update an entity and its fields."""
    data = request.get_json()

    schema_id = data.get('schema_id')
    entity_name = data.get('entity_name')
    entity_description = data.get('entity_description')
    fields_data = data.get('fields')

    if not schema_id or not entity_name or not fields_data:
        return jsonify({"error": "Schema ID, entity name, and fields are required."}), 400

    try:
        entity = insert_or_update_entity(
            schema_id=schema_id,
            entity_name=entity_name,
            entity_description=entity_description,
            fields_data=fields_data
        )
        return generateResponse({
            "message": "Entity inserted/updated successfully.",
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "description": entity.description,
                "fields": [
                    {
                        "name": field.name,
                        "description": field.description
                    } for field in entity.fields
                ]
            }
        }, 201)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

@app.route('/api/entity/<int:entity_id>', methods=['DELETE'])
def api_delete_entity(entity_id):
    """API to delete an entity and its associated fields."""
    try:
        # Call the delete_entity function
        deleted = delete_entity(entity_id)

        if not deleted:
            return jsonify({"error": "Entity not found."}), 404

        return generateResponse({"message": "Entity deleted successfully."}, 200)

    except Exception as e:
        return generateResponse({"error": f"An error occurred: {e}"}, 500)

def delete_entity(entity_id):
    """
    Deletes an entity and its associated fields from the database.

    Args:
        entity_id (int): The ID of the entity to delete.

    Returns:
        bool: True if the entity was successfully deleted, False otherwise.
    """

    # Find the entity by ID
    entity = Entity.query.get(entity_id)
    if not entity:
        return False

    # Delete the entity and its associated fields
    db.session.delete(entity)
    db.session.commit()

    return True

@app.route('/upload-schema', methods=['POST'])
def upload_schema():
    """API to upload a schema, its entities, and their fields with descriptions."""
    data = request.get_json()
    
    schema_name = data.get('schema_name')
    schema_description = data.get('schema_description')
    entities_data = data.get('entities')

    if not schema_name or not entities_data:
        return jsonify({"error": "Schema name and entities are required."}), 400

    # Create schema entry
    schema = Schema(name=schema_name, description=schema_description)
    db.session.add(schema)
    db.session.commit()

    for entity_data in entities_data:
        entity_name = entity_data.get('name')
        entity_description = entity_data.get('description')
        fields_data = entity_data.get('fields')

        if not entity_name or not fields_data:
            continue

        # Create entity entry
        entity = Entity(name=entity_name, description=entity_description, schema_id=schema.id)
        db.session.add(entity)
        db.session.commit()

        for field_data in fields_data:
            field_name = field_data.get('name')
            field_description = field_data.get('description')

            # Create field entry
            field = Field(name=field_name, description=field_description, entity_id=entity.id)
            db.session.add(field)

        db.session.commit()

    return generateResponse({"message": "Schema and entities uploaded successfully."}, 201)

@app.route('/schemas/', methods=['GET'])
def get_all_schemas():
    """API to retrieve all schemas along with their entities and fields."""
    schemas = Schema.query.all()
    result = []

    for schema in schemas:
        entities = []
        for entity in schema.entities:
            fields = [
                {"id": field.id, "name": field.name, "description": field.description} 
                for field in entity.fields
            ]
            entities.append({
                "id": entity.id,
                "name": entity.name,
                "description": entity.description,
                "fields": fields
            })
        
        result.append({
            "id": schema.id,
            "name": schema.name,
            "description": schema.description,
            "entities": entities
        })

    return generateResponse(result, 200)

@app.route('/entities/<int:schema_id>/', methods=['GET'])
def list_entities(schema_id):
    """API to retrieve all entities in a specified schema."""
    try:
        entities = get_schema_entities(schema_id)

        if not entities:
            return jsonify({"error": f"No entities found for schema_id {schema_id}"}), 404

        # Return the entities as JSON
        response = []
        for entity_name, entity_data in entities.items():
            response.append({
                "name": entity_name,
                "description": entity_data["description"],
                "fields": entity_data["fields"]
            })

        return generateResponse(response, 200)

    except Exception as e:
        return generateResponse({"error": f"An error occurred: {str(e)}"}, 500)

def insert_or_update_schema(schema_name, schema_description=None):
    """
    Inserts a new schema or updates an existing schema.

    Args:
        schema_name (str): The name of the schema.
        schema_description (str): Optional description of the schema.

    Returns:
        Schema: The inserted or updated schema object.
    """
    # Check if schema exists
    schema = Schema.query.filter_by(name=schema_name).first()

    if schema:
        # Update schema description if necessary
        schema.description = schema_description
    else:
        # Create a new schema
        schema = Schema(name=schema_name, description=schema_description)
        db.session.add(schema)

    # Commit the transaction
    db.session.commit()
    return schema


def insert_or_update_entity(schema_id, entity_name, entity_description=None, fields_data=None):
    """
    Inserts a new entity or updates an existing entity and its fields.

    Args:
        schema_id (int): The ID of the schema the entity belongs to.
        entity_name (str): The name of the entity.
        entity_description (str): Optional description of the entity.
        fields_data (list): A list of field dictionaries with 'name' and 'description'.

    Returns:
        Entity: The inserted or updated entity object.
    """
    if not schema_id:
        raise ValueError("Schema ID is required to associate an entity.")

    # Check if entity exists
    entity = Entity.query.filter_by(name=entity_name, schema_id=schema_id).first()

    if entity:
        # Update entity description
        entity.description = entity_description

        # Delete all existing fields for the entity
        Field.query.filter_by(entity_id=entity.id).delete()
    else:
        # Create a new entity
        entity = Entity(name=entity_name, description=entity_description, schema_id=schema_id)
        db.session.add(entity)
        db.session.commit()  # Commit to get the entity ID

    # Add new fields
    if fields_data:
        for field_data in fields_data:
            field_name = field_data.get('name')
            field_description = field_data.get('description')

            if not field_name:
                continue

            # Create field entry
            field = Field(name=field_name, description=field_description, entity_id=entity.id)
            db.session.add(field)

    # Commit the transaction
    db.session.commit()
    return entity

@app.route('/match-entities/', methods=['POST'])
def match_entities():
    """API to match fields of an entity between schemas."""
    data = request.get_json()
    source_schema_id = data.get("source_schema_id")
    target_schema_id = data.get("target_schema_id")
    source_entity_name = data.get("source_entity_name")
    target_entity_name = data.get("target_entity_name")
    ignore_db = data.get("ignore_db", False)  # Default to False

    # Validate inputs
    if not all([source_schema_id, target_schema_id, source_entity_name, target_entity_name]):
        return jsonify({"error": "All fields are required."}), 400

    # Check the database first (mock function `get_matching_data_from_db`)
    if not ignore_db:
        db_data = get_matching_data_from_db(
            source_schema_id, target_schema_id, source_entity_name, target_entity_name
        )
        if db_data:
            return jsonify({"field_mappings": db_data}), 200

    # Retrieve entities
    source_entities = get_schema_entities(source_schema_id)
    target_entities = get_schema_entities(target_schema_id)

    if source_entity_name not in source_entities or target_entity_name not in target_entities:
        return jsonify({"error": "Entity not found in the specified schema."}), 404

    source_fields = source_entities[source_entity_name]["fields"]
    target_fields = target_entities[target_entity_name]["fields"]

    # Perform field matching using external match function
    field_mappings = match_fields(source_fields, target_fields)

    # Store the result in the database for future queries (mock function `store_matching_data_in_db`)
    store_matching_data_in_db(
        source_schema_id, target_schema_id, source_entity_name, target_entity_name, field_mappings
    )

    return generateResponse({"field_mappings": field_mappings}, 200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
