import faiss
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from openai import OpenAI

from app.database import fetch_entity_embeddings, get_schema_entities, store_embedding

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

config = {
    "models": [
        {"name": "openai", "use": lambda api_key: bool(api_key)},
        {"name": "distilbert-base-nli-mean-tokens", "instance": SentenceTransformer("sentence-transformers/distilbert-base-nli-mean-tokens").to(device)},
        {"name": "msmarco-distilbert-base-v3", "instance": SentenceTransformer("sentence-transformers/msmarco-distilbert-base-v3").to(device)},
        {"name": "all-mpnet-base-v2", "instance": SentenceTransformer("sentence-transformers/all-mpnet-base-v2").to(device)},
        {"name": "multi-qa-mpnet-base-dot-v1", "instance": SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1").to(device)},
        {"name": "colbertv2.0", "instance": SentenceTransformer("colbert-ir/colbertv2.0").to(device)},
    ],
    "openai_api_key": ""
}

client = None
if (config.get("openai_api_key")):
    client = OpenAI(api_key=config.get("openai_api_key"))

def add_embeddings_to_faiss(embeddings, faiss_index, metadata_mapping):
    """
    Add embeddings to a FAISS index.

    Args:
        embeddings (list): List of embeddings and their metadata.
        faiss_index (faiss.Index): FAISS index to populate.
        metadata_mapping (dict): Mapping of FAISS indices to metadata.
    """
    for i, embedding in enumerate(embeddings):
        faiss_index.add(np.array([embedding["embedding"]], dtype="float32"))
        metadata_mapping[len(metadata_mapping)] = {
            "entity_id": embedding["entity_id"],
            "field_id": embedding["field_id"],
            "description": embedding["description"]
        }

def search_embeddings(source_text, model, faiss_index, metadata_mapping, k=5):
    """
    Search for the nearest neighbors of a given source text in the FAISS index.

    Args:
        source_text (str): Source text to embed and search.
        model (SentenceTransformer): Model for generating embeddings.
        faiss_index (faiss.Index): FAISS index to search.
        metadata_mapping (dict): Mapping of FAISS indices to metadata.
        k (int): Number of nearest neighbors to retrieve.

    Returns:
        List[dict]: List of nearest neighbors and their metadata.
    """
    source_embedding = model.encode([source_text], convert_to_tensor=False)[0]
    source_embedding = np.array([source_embedding], dtype="float32")
    
    distances, indices = faiss_index.search(source_embedding, k)
    results = []
    for idx, distance in zip(indices[0], distances[0]):
        if idx == -1:
            continue
        metadata = metadata_mapping[idx]
        metadata["distance"] = distance
        results.append(metadata)
    return results

def generate_embeddings(model_config, field):
    text = f"Field: {field['name'].replace('_', ' ')}. Description: {field['description']}"
    if model_config["name"] == "openai":
        if not client:
            return None
        response = client.embeddings.create(input=text, model="text-embedding-ada-002")
        embedding = response.data[0].embedding
        embedding = torch.tensor(embedding)
        return embedding
    else:
        model = model_config["instance"]
        try:
            embedding = model.encode([text], convert_to_tensor=True)[0]
            return embedding.cpu()
        except Exception as e:
            print(e)
            return None



def match_fields(source_entity, target_entities, model_name):
    """
    Matches fields between source and target entities using multiple embedding models.

    Args:
        source_entity (Entity): source entity.
        target_entities (list): List of entities to map to
        model_name (str): Name of model to use.
    Returns:
        dict: A mapping where the key is the source field name, and the value is list of top 5 matches across
              all models.
    """
    model = next((x for x in config["models"] if x["name"] == model_name), None)
    all_entities = {source_entity["id"]: source_entity}
    for entity in target_entities:
        all_entities[entity["id"]] = entity

    for entity_id, entity in all_entities.items():
        entity_embeddings = fetch_entity_embeddings([entity_id], model_name)
        # All or none for now. If an entity field is added, the whole entity has to be regenerated.
        # TODO: add logic to check for missing field embeddings and regenerate
        if not entity_embeddings:
            entity_embeddings = [{
                "field": {"id": field["id"], "name": field["name"], "description": field["description"]},
                "entity_id": entity_id,
                "model_name": model_name,
                "embedding": generate_embeddings(model, field)
            } for field in entity["fields"]]
            [store_embedding(field_embedding["field"]["id"], model_name, field_embedding["embedding"]) for field_embedding in entity_embeddings]
        all_entities[entity["id"]]["embeddings"] = entity_embeddings

    field_mappings = {}

    # Initialize FAISS index. TODO: DONT hardcode 768
    metadata_mapping = {}

    target_embeddings = [embedding for target_entity in target_entities for embedding in target_entity["embeddings"]]

    # Add target embeddings to the FAISS index
    if target_embeddings:
        embeddings = np.array([item["embedding"] for item in target_embeddings]).astype("float32")
        print(embeddings.shape)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)  # Reshape to (1, embedding_dimension)
        elif embeddings.ndim == 2:
            pass  # Already 2D, no need to reshape
        else:
            raise ValueError("Embeddings should be a 1D or 2D array")

        embedding_dimension = embeddings.shape[1]
        faiss_index = faiss.IndexFlatL2(embedding_dimension)
        faiss_index.add(embeddings)
        metadata_mapping = {i: target_embeddings[i] for i in range(len(target_embeddings))}

    # Process source fields
    for source_field_embedding in source_entity["embeddings"]:
        source_field = source_field_embedding["field"]
        source_field_name = source_field["name"]
        source_text = f"Field: {source_field_name.replace('_', ' ')}. Description: {source_field['description']}"

        source_embedding = source_field_embedding["embedding"]

        # Search FAISS for top matches
        if faiss_index.ntotal > 0:
            distances, indices = faiss_index.search(np.array(source_embedding, dtype="float32").reshape(1, -1), k=5)
            if all(idx == -1 for idx in indices[0]):
                matches = []
            else:
                matches = [
                    {
                        "target_entity_id": metadata_mapping[idx]["entity_id"],
                        "target_field_id": metadata_mapping[idx]["field"]["id"],
                        "target_field_name": metadata_mapping[idx]["field"]["name"],
                        "target_field_description": metadata_mapping[idx]["field"]["description"],
                        "score": 1 - distances[0][i],  # FAISS uses L2 distance; convert to similarity
                    }
                    for i, idx in enumerate(indices[0])
                    if idx != -1  # Skip indices that are -1
                ]

            field_mappings[source_field_name] = matches

    return field_mappings

# Not used after switching to FAISS but may use it again later.
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