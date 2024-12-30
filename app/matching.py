from app.colbert_handler import search_target_schema
from app.llm_handler import query_llm
from sklearn.preprocessing import MinMaxScaler

def match_entities(source_schema_id, target_schema_id, entity_name):
    # Fetch schemas from database
    source_schema = get_schema(source_schema_id)
    target_schema = get_schema(target_schema_id)
    
    source_entity = source_schema["entities"].get(entity_name)
    if not source_entity:
        raise ValueError(f"Entity '{entity_name}' not found in source schema.")

    # Create query for source entity
    source_query = f"{entity_name}: {source_entity['description']}"

    # ColBERT matches
    colbert_matches = search_target_schema(source_query)

    # LLM matches (optional)
    llm_matches = query_llm(source_query, target_schema["entities"])

    # Combine results and rank
    # You can add ranking logic here
    matches = colbert_matches + llm_matches
    return matches

def normalize_scores(scores):
    scaler = MinMaxScaler()
    return scaler.fit_transform([[score] for score in scores]).flatten()

def rank_candidates(colbert_matches, llm_matches, weight_colbert=0.7, weight_llm=0.3):
    colbert_scores = {match[0]: match[1] for match in colbert_matches}
    llm_scores = {match[0]: match[1] for match in llm_matches}

    # Combine results
    all_candidates = set(colbert_scores.keys()).union(set(llm_scores.keys()))

    # Normalize scores
    colbert_scores = normalize_scores(list(colbert_scores.values()))
    llm_scores = normalize_scores(list(llm_scores.values()))

    # Combine with weighted sum
    combined_scores = {}
    for candidate in all_candidates:
        colbert_score = colbert_scores.get(candidate, 0)
        llm_score = llm_scores.get(candidate, 0)
        combined_scores[candidate] = weight_colbert * colbert_score + weight_llm * llm_score

    # Sort candidates
    return sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
