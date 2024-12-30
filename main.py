from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import torch
from app.colbert_handler import embed_text
from app.utils import generate_embeddings, rank_candidates, rank_candidates_pytorch
from app.llm_handler import query_llm
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from app.database import db, Schema, Entity, Field
import json

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

    # Generate text descriptions
    # source_fields_text = [f"{field}" for field in source_fields]
    # target_fields_text = [f"{field}" for field in target_fields]
    source_fields_text = [f"{field['name']}: {field['description']}" for field in source_fields]
    target_fields_text = [f"{field['name']}: {field['description']}" for field in target_fields]

    # Rank entity-level similarity
    ranked_by_model = rank_candidates(" ".join(source_fields_text), target_fields_text)
    # ranked_by_llm = query_llm(" ".join(source_fields_text), target_fields_text)
    # combined_results = sorted(ranked_by_model + ranked_by_llm, key=lambda x: x[1], reverse=True)
    combined_results = sorted(ranked_by_model, key=lambda x: x[1], reverse=True)
    # Compute field-to-field mappings
    field_mappings = []
    for source_field in source_fields:
        # Embed both the name and description for the source field
        source_embedding = embed_text_with_context(source_field['name'], source_field['description'])
        
        # Generate embeddings for the target fields (name + description)
        target_embeddings = [
            embed_text_with_context(target_field['name'], target_field['description']) 
            for target_field in target_fields
        ]
        # source_embedding = generate_embeddings(source_field.replace("_", " "))
        # target_embeddings = [generate_embeddings(target_field.replace("_", " ")) for target_field in target_fields]

        # Compute similarity for each field
        field_similarities = rank_candidates_pytorch(source_embedding, torch.stack(target_embeddings))
        for target_index, score in field_similarities:
            field_mappings.append({
                "source_field": source_field,
                "target_field": target_fields[target_index],
                "score": float(score)
            })
    # Convert all numerical values to native Python types (int, float)
    def convert_to_native(obj):
        if isinstance(obj, np.int64):
            return int(obj)
        elif isinstance(obj, np.float64):
            return float(obj)
        elif isinstance(obj, list):
            return [convert_to_native(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_to_native(value) for key, value in obj.items()}
        return obj
    
    print(combined_results)
    # Convert results to ensure compatibility with JSON serialization
    combined_results = [(
        convert_to_native(result[0]),  # index remains the same
        convert_to_native(result[1])  # Convert the score
    ) for result in combined_results]

    field_mappings = [convert_to_native(mapping) for mapping in field_mappings]

    return generateResponse({
        "entity_similarity": [
            {"index": result[0], "score": float(result[1])} for result in combined_results
        ],
        "field_mappings": field_mappings
    }, 200)

def embed_text_with_context(field_name, description):
    context = f"Field: {field_name.replace("_", " ")}. Description: {description}"
    return generate_embeddings(context)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
