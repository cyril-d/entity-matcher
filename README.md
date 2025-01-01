# Schema Mapper Tool

## Overview
This tool provides schema matching capabilities using ColBERTv2 for semantic similarity and LLM-based ranking. It includes APIs for schema management, matching, and ranking.

## Features
- Upload schemas with entities and fields
- Scan OpenAPI/Swagger specs to extract entities for a schema and store it in the database.
- Match fields between schemas using semantic similarity
- Embeddings used: openai, msmarco-distilbert-base-v3, all-mpnet-base-v2, multi-qa-mpnet-base-dot-v1, colbertv2.0
- Combine these model matches with LLM for ranking (TBD)

## Requirements
- Python 3.9+
- Docker (TBD)

## Running Locally
1. Install dependencies:
   ```bash
   pip install sqlite
   pip install -r requirements.txt
   python -c "from app.database import initialize_db; initialize_db()"
   python main.py
   
Run tests optionally: pytest tests - doesnt work yet
