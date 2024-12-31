from flask_sqlalchemy import SQLAlchemy

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
    source_schema_id = db.Column(db.Integer, nullable=False)
    target_schema_id = db.Column(db.Integer, nullable=False)
    source_entity_name = db.Column(db.String(100), nullable=False)
    target_entity_name = db.Column(db.String(100), nullable=False)
    field_mappings = db.Column(db.JSON, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'source_schema_id', 'target_schema_id', 
            'source_entity_name', 'target_entity_name', 
            name='unique_field_match'
        ),
    )

def store_matching_data_in_db(source_schema_id, target_schema_id, source_entity_name, target_entity_name, field_mappings):
    """
    Stores matching data into the database.

    Args:
        source_schema_id (int): ID of the source schema.
        target_schema_id (int): ID of the target schema.
        source_entity_name (str): Name of the source entity.
        target_entity_name (str): Name of the target entity.
        field_mappings (dict): Field mapping data in JSON format.
    """
    try:
        # Check if the record already exists
        field_match = FieldMatch.query.filter_by(
            source_schema_id=source_schema_id,
            target_schema_id=target_schema_id,
            source_entity_name=source_entity_name,
            target_entity_name=target_entity_name
        ).first()

        if field_match:
            # Update the existing record
            field_match.field_mappings = field_mappings
        else:
            # Insert a new record
            field_match = FieldMatch(
                source_schema_id=source_schema_id,
                target_schema_id=target_schema_id,
                source_entity_name=source_entity_name,
                target_entity_name=target_entity_name,
                field_mappings=field_mappings
            )
            db.session.add(field_match)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Error storing matching data in the database: {e}")

def get_matching_data_from_db(source_schema_id, target_schema_id, source_entity_name, target_entity_name):
    """
    Retrieves matching data from the database.

    Args:
        source_schema_id (int): ID of the source schema.
        target_schema_id (int): ID of the target schema.
        source_entity_name (str): Name of the source entity.
        target_entity_name (str): Name of the target entity.

    Returns:
        dict or None: Field mapping data in JSON format if found, otherwise None.
    """
    try:
        field_match = FieldMatch.query.filter_by(
            source_schema_id=source_schema_id,
            target_schema_id=target_schema_id,
            source_entity_name=source_entity_name,
            target_entity_name=target_entity_name
        ).first()

        if field_match:
            return field_match.field_mappings

        return None
    except Exception as e:
        raise RuntimeError(f"Error retrieving matching data from the database: {e}")
