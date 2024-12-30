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
