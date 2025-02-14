# Schema Mapper Tool

## Overview
This tool provides schema matching capabilities using ColBERTv2 and other models for semantic similarity and LLM-based ranking. It includes APIs for schema management, matching, and ranking.

## Features
- api_entity_extractor.py: Scan OpenAPI yaml/Swagger json specs to extract entities for a schema and store it in the database.
- api_entity_extractor.py: parse csv schemas with entities and fields
- Match fields between schemas using semantic similarity
- Embeddings used: openai, msmarco-distilbert-base-v3, all-mpnet-base-v2, multi-qa-mpnet-base-dot-v1, colbertv2.0
- Combine these model matches with LLM prompts for ranking (To Be Done)
- Train models on incorrect matches or user corrected matches (To Be Done)

## Requirements
- Python 3.9+
- Docker (TBD)

## Database Stuff
Using sqlite for now. The schema and all db access code is in database.py. The schema had to be changed multiple times and was done using alembic, but note alembic does have issues and sometimes I just had to use sqllite3 to connect to the db and modify the schema
The db also stores all model embeddings (once generated) to save cost when using openai. To search, we load the embeddings into a FAISS index at runtime and then do a top 5 search.  

### Entity Extractor
python api_entity_extractor.py <input_file> <schema_name> <schema_description>

See adc-sources.txt for a sample input file.

### Sample Queries (For my reference)
#### Fetch an entity:
select * from entities where entities.name='Position';

#### Get embeddings for an entity: 
select * from embeddings join fields on embeddings.field_id = fields.id and fields.entity_id in (22, 23, 153);
#### Delete these embeddings: 
delete from embeddings where id in (select e.id from embeddings e join fields on e.field_id = fields.id and fields.entity_id in (22, 23, 153));

## Running Locally
1. Install dependencies:
   ```bash
   pip install sqlite
   pip install -r requirements.txt
   python -c "from app.database import initialize_db; initialize_db()"
   python main.py
   
## Tests

pytest tests - doesnt work yet

## API Usage

1. Upsert Schema:

curl --request POST \
  --url http://127.0.0.1:8000/api/schema \
  --header 'Content-Type: application/json'
  --data '{
  "schema_name": "CustomerSchemaD",
  "schema_description": "Customer related data"
}
'

2. Upsert Entity:

curl --request POST \
  --url http://127.0.0.1:8000/api/entity \
  --header 'Content-Type: application/json'
  --data '{
  "schema_id": 4,
  "entity_name": "Customer",
	"entity_description": "Details about the customer",
	"fields": [
		{"name": "customername", "description": "The full name of the customer"},
		{"name": "email", "description": "The email address of the customer"},
		{"name": "phone", "description": "The phone number of the customer"}
	]
}
'

3. Get Schema by id:

curl --request GET \
  --url http://127.0.0.1:8000/api/schema/4 \
  --header 'Content-Type: application/json'

4. List entities in a schema:

curl --request GET \
  --url http://127.0.0.1:8000/api/entities/4/ \
  --header 'Content-Type: application/json'

5. Get Entity by id:

curl --request GET \
  --url http://127.0.0.1:8000/api/entity/7 \
  --header 'Content-Type: application/json'

6. List Schemas:

curl --request GET \
  --url http://127.0.0.1:8000/api/schemas/ \
  --header 'Content-Type: application/json' 

7. Match Entities:

curl --request POST \
  --url http://127.0.0.1:8000/api/match-entities/ \
  --header 'Content-Type: application/json' \
  --data '{
    "source_schema_id": 1,
    "target_schema_id": 2,
    "source_entity_name": "Customer",
	  "target_entity_name": "Customer"
}
'
