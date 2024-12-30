# Schema Mapper Tool

## Overview
This tool provides schema matching capabilities using ColBERTv2 for semantic similarity and LLM-based ranking. It includes APIs for schema management, matching, and ranking.

## Features
- Upload schemas with field descriptions
- Match fields between schemas using semantic similarity
- Combine ColBERTv2 and LLM for ranking

## Requirements
- Python 3.9+
- Docker (optional)

## Running Locally
1. Install dependencies:
   ```bash
   pip install sqlite
   pip install -r requirements.txt
   python -c "from app.database import initialize_db; initialize_db()"

   pytest tests
