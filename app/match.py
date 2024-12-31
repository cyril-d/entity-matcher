import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from openai import OpenAI

# Configuration for embedding models
config = {
    "models": [
        {"name": "openai", "use": lambda api_key: bool(api_key)},
        {"name": "msmarco-distilbert-base-v3", "instance": SentenceTransformer("sentence-transformers/msmarco-distilbert-base-v3")},
        {"name": "all-mpnet-base-v2", "instance": SentenceTransformer("sentence-transformers/all-mpnet-base-v2")},
        {"name": "multi-qa-mpnet-base-dot-v1", "instance": SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")},
        {"name": "colbertv2.0", "instance": SentenceTransformer("colbert-ir/colbertv2.0")},
    ],
    "openai_api_key": ""
}

client = None
if (config.get("openai_api_key")):
    client = OpenAI(api_key=config.get("openai_api_key"))

def match_fields(source_fields, target_fields):
    """
    Matches fields between source and target entities using multiple embedding models.

    Args:
        source_fields (list): List of source fields with 'name' and 'description'.
        target_fields (list): List of target fields with 'name' and 'description'.

    Returns:
        dict: A mapping where the key is the source field name, and the value is another dictionary
              with model names as keys and an array of target field matches ordered by score as values.
    """
    field_mappings = {}

    for source_field in source_fields:
        source_field_name = source_field['name']
        source_text = f"Field: {source_field_name.replace('_', ' ')}. Description: {source_field['description']}"
        model_matches = {}

        # Generate embeddings with multiple models
        for model_config in config["models"]:
            if model_config["name"] == "openai":
                if not client:
                    continue;
                
                response = client.embeddings.create(input=source_text, model="text-embedding-ada-002")
                source_embedding = response.data[0].embedding
                    
                target_embeddings = [
                    response.data[0].embedding
                    for target_field in target_fields
                    for response in [client.embeddings.create(
                        input=f"Field: {target_field['name'].replace('_', ' ')}. Description: {target_field['description']}",
                        model="text-embedding-ada-002"
                    )]
                ]

                source_embedding = torch.tensor(source_embedding)
                target_embeddings = torch.tensor(target_embeddings)

            else:
                model = model_config["instance"]
                source_embedding = model.encode([source_text], convert_to_tensor=True)[0]
                target_embeddings = torch.stack([
                    model.encode(f"Field: {target_field['name'].replace('_', ' ')}. Description: {target_field['description']}", convert_to_tensor=True)
                    for target_field in target_fields
                ])

            # Compute similarity scores
            field_similarities = rank_candidates_pytorch(source_embedding, target_embeddings)
            model_matches[model_config["name"]] = [
                {
                    "target_field_name": target_fields[target_index]["name"],
                    "target_field_description": target_fields[target_index]["description"],
                    "score": float(score)
                }
                for target_index, score in field_similarities
            ]

        # Add matches for this source field
        field_mappings[source_field_name] = model_matches

    return field_mappings

def rank_candidates_pytorch(source_embedding, target_embeddings):
    """
    Rank target embeddings based on cosine similarity to the source embedding.

    Args:
        source_embedding (torch.Tensor): The source embedding (1D Tensor).
        target_embeddings (torch.Tensor): The target embeddings (2D Tensor).

    Returns:
        List[Tuple[int, float]]: List of (index, similarity score) sorted by similarity.
    """
    similarities = torch.nn.functional.cosine_similarity(
        source_embedding.unsqueeze(0), target_embeddings, dim=1
    )
    ranked_indices = torch.argsort(similarities, descending=True)
    return [(idx.item(), similarities[idx].item()) for idx in ranked_indices]