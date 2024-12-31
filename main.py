from flask import Flask, request, jsonify
from flask_cors import CORS
from app.match import match_fields
from app.database import db, Schema, Entity, Field

app = Flask(__name__)
CORS(app)  # Allow CORS for all routes
# CORS(app, resources={r"/schemas/*": {"origins": "http://localhost:3000"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schemas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.after_request
def add_security_headers(resp):
    resp.headers['Access-Control-Allow-Origin']='http://localhost:3000'
    resp.headers['Access-Control-Allow-Methods']='GET, POST, PUT, OPTIONS'
    resp.headers["Access-Control-Allow-Headers"]="Access-Control-Request-Headers,Access-Control-Allow-Methods,Access-Control-Allow-Headers,Access-Control-Allow-Origin, Origin, X-Requested-With, Content-Type, Accept"
    return resp

@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        response = app.make_response('')
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

def generateResponse(json, statusCode):
    response = jsonify(json)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.status_code = statusCode
    print(response)
    return response;

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
                {"name": field.name, "description": field.description} 
                for field in entity.fields
            ]
            entities.append({
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

def get_schema_entities(schema_id):
    """Helper to get all entities of a specific schema."""
    schema = Schema.query.get(schema_id)
    if not schema:
        return {}
    
    entities = {}
    for entity in schema.entities:
        fields = [{"name": field.name, "description": field.description} for field in entity.fields]
        entities[entity.name] = {"description": entity.description, "fields": fields}
    
    return entities

@app.route('/entities/<int:schema_id>/', methods=['GET'])
def list_entities(schema_id):
    """API to retrieve all entities in a specified schema."""
    try:
        # Use the get_schema_entities function
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


@app.route('/match-entities/', methods=['POST'])
def match_entities():
    """API to match fields of an entity between schemas."""
    data = request.get_json()
    source_schema_id = data.get("source_schema_id")
    target_schema_id = data.get("target_schema_id")
    source_entity_name = data.get("source_entity_name")
    target_entity_name = data.get("target_entity_name")

    # Validate inputs
    if not all([source_schema_id, target_schema_id, source_entity_name, target_entity_name]):
        return jsonify({"error": "All fields are required."}), 400

    # Retrieve entities
    source_entities = get_schema_entities(source_schema_id)
    target_entities = get_schema_entities(target_schema_id)

    if source_entity_name not in source_entities or target_entity_name not in target_entities:
        return jsonify({"error": "Entity not found in the specified schema."}), 404

    source_fields = source_entities[source_entity_name]["fields"]
    target_fields = target_entities[target_entity_name]["fields"]

    # Perform field matching using external match function
    field_mappings = match_fields(source_fields, target_fields)

    return generateResponse({"field_mappings": field_mappings}, 200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
