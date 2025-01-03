from flask_sqlalchemy import SQLAlchemy
import numpy as np

db = SQLAlchemy()

class Schema(db.Model):
    __tablename__ = 'schemas'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    entities = db.relationship('Entity', backref='schema', lazy=True)

class Entity(db.Model):
    __tablename__ = 'entities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    schema_id = db.Column(db.Integer, db.ForeignKey('schemas.id'), nullable=False)
    fields = db.relationship('Field', backref='entity', lazy=True)

class Field(db.Model):
    __tablename__ = 'fields'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    entity_id = db.Column(db.Integer, db.ForeignKey('entities.id'), nullable=False)

class FieldMatch(db.Model):
    __tablename__ = 'field_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    source_entity_id = db.Column(db.Integer, db.ForeignKey('entities.id'), nullable=False)
    model_name = db.Column(db.String, nullable=False)
    field_mappings = db.Column(db.JSON, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'source_entity_id',
            name='unique_field_match'
        ),
    )

class Embedding(db.Model):
    __tablename__ = 'embeddings'
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
    model_name = db.Column(db.String, nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)

def insert_or_update_schema(schema_name, schema_description=None):
    schema = Schema.query.filter_by(name=schema_name).first()

    if schema:
        schema.description = schema_description
    else:
        schema = Schema(name=schema_name, description=schema_description)
        db.session.add(schema)

    db.session.commit()
    return schema

def insert_or_update_entity(schema_id, entity_name, entity_description=None, fields_data=None):
    entity = Entity.query.filter_by(name=entity_name, schema_id=schema_id).first()

    if entity:
        entity.description = entity_description
        Field.query.filter_by(entity_id=entity.id).delete()
    else:
        entity = Entity(name=entity_name, description=entity_description, schema_id=schema_id)
        db.session.add(entity)
        db.session.commit()

    if fields_data:
        for field_data in fields_data:
            field = Field(
                name=field_data.get('name'),
                description=field_data.get('description'),
                entity_id=entity.id
            )
            db.session.add(field)

    db.session.commit()
    return entity

def add_field(schema_id, entity_name, entity_description, fields_data=None):
    entity = Entity.query.filter_by(name=entity_name, schema_id=schema_id).first()

    if not entity:
        entity = Entity(name=entity_name, description=entity_description, schema_id=schema_id)
        db.session.add(entity)
        db.session.commit()

    if fields_data:
        for field_data in fields_data:
            field = Field(
                name=field_data.get('name'),
                description=field_data.get('description'),
                entity_id=entity.id
            )
            db.session.add(field)

    db.session.commit()
    return entity

def delete_entity(entity_id):
    entity = Entity.query.get(entity_id)
    if not entity:
        return False

    db.session.delete(entity)
    db.session.commit()
    return True

def get_all_schemas():
    schemas = Schema.query.all()
    result = []
    for schema in schemas:
        entities = []
        for entity in schema.entities:
            fields = [{"id": field.id, "name": field.name, "description": field.description} for field in entity.fields]
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
    return result

def get_schema_by_id(schema_id):
    schema = Schema.query.get(schema_id)
    if not schema:
        return None

    entities = []
    for entity in schema.entities:
        fields = [{"id": field.id, "name": field.name, "description": field.description} for field in entity.fields]
        entities.append({
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "fields": fields
        })

    return {
        "id": schema.id,
        "name": schema.name,
        "description": schema.description,
        "entities": entities
    }

def get_schema_entities(schema_id):
    """Helper to get all entities of a specific schema."""
    schema = Schema.query.get(schema_id)
    if not schema:
        return None
    
    entities = {}
    for entity in schema.entities:
        fields = [{"id": field.id, "name": field.name, "description": field.description} for field in entity.fields]
        entities[entity.name] = {"id": entity.id, "description": entity.description, "fields": fields}
    
    return entities

def get_entity_by_id(entity_id):
    entity = Entity.query.get(entity_id)
    if not entity:
        return None

    fields = [{"id": field.id, "name": field.name, "description": field.description} for field in entity.fields]
    return {
        "id": entity.id,
        "name": entity.name,
        "description": entity.description,
        "schema_id": entity.schema_id,
        "fields": fields
    }

def get_entities_by_ids(entity_ids):
    entities = Entity.query.filter(Entity.id.in_(entity_ids)).all()

    return [{
        "id": entity.id,
        "name": entity.name,
        "description": entity.description,
        "schema_id": entity.schema_id,
        "fields": [{"id": field.id, "name": field.name, "description": field.description}
                   for field in entity.fields]
    } for entity in entities]

def get_entity_by_name(schema_id, entity_name):
    entity = Entity.query.filter_by(
        schema_id=schema_id,
        name=entity_name
    ).first()

    if not entity:
        return None
    else:
        fields = [{"id": field.id, "name": field.name, "description": field.description} for field in entity.fields]
        return {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "schema_id": entity.schema_id,
            "fields": fields
        }


def get_entities_by_names(schema_id, entity_names):
    entities = Entity.query.filter(
        Entity.schema_id == schema_id,
        Entity.name.in_(entity_names)
    ).all()

    return [{
        "id": entity.id,
        "name": entity.name,
        "description": entity.description,
        "schema_id": entity.schema_id,
        "fields": [{"id": field.id, "name": field.name, "description": field.description}
                   for field in entity.fields]
    } for entity in entities]

def store_matching_data_in_db(source_entity, model_name, field_mappings):
    try:
        # Check if the record already exists
        field_match = FieldMatch.query.filter_by(
            source_entity_id=source_entity["id"],
            model_name=model_name,
        ).first()

        if field_match:
            # Update the existing record
            field_match.field_mappings = field_mappings
        else:
            # Insert a new record
            field_match = FieldMatch(
                source_entity_id=source_entity["id"],
                model_name=model_name,
                field_mappings=field_mappings
            )
            db.session.add(field_match)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Error storing matching data in the database: {e}")


def get_matching_data_from_db(source_entity, model_name):
    try:
        field_match = FieldMatch.query.filter_by(
            source_entity_id=source_entity["id"],
            model_name=model_name
        ).first()

        if field_match:
            return field_match.field_mappings

        return None
    except Exception as e:
        raise RuntimeError(f"Error retrieving matching data from the database: {e}")

def store_embedding(field_id, model_name, embedding):
    """
    Store an embedding in the database.
    """
    existing = Embedding.query.filter_by(
        field_id=field_id, model_name=model_name
    ).first()
    if existing:
        existing.embedding = np.array(embedding, dtype="float32").tobytes()
    else:
        new_embedding = Embedding(
            field_id=field_id,
            model_name=model_name,
            embedding=np.array(embedding, dtype="float32").tobytes(),
        )
        db.session.add(new_embedding)
    db.session.commit()

def fetch_embedding(field_id, model_name):
    """
    Fetch an embedding from the database.
    """
    embedding = Embedding.query.filter_by(
        field_id=field_id, model_name=model_name
    ).first()
    if embedding:
        return np.frombuffer(embedding.embedding, dtype="float32")
    return None

def fetch_entity_embeddings(entity_ids, model_name):
    """
    Fetch all embeddings for the target entities and their fields.
    """
    embeddings = []
    fields = (
        db.session.query(Field, Embedding)
        .join(Embedding, Embedding.field_id == Field.id)
        .filter(Field.entity_id.in_(entity_ids), Embedding.model_name == model_name)
        .all()
    )

    for field, embedding in fields:
        embeddings.append({
            "embedding": np.frombuffer(embedding.embedding, dtype="float32"),
            "field": {"id": field.id, "name": field.name, "description": field.description},
            "entity_id": field.entity_id,
            "model_name": embedding.model_name,
        })
    return embeddings
