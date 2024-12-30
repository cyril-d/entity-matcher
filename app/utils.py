from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F

from app.colbert_handler import embed_text

# Load the SentenceTransformer model for embeddings
# model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2') # Very good one
model = SentenceTransformer('sentence-transformers/multi-qa-mpnet-base-dot-v1')

def generate_embeddings(text_list):
    """Generates embeddings for a list of text fields."""
    return model.encode(text_list, convert_to_tensor=True)

def rank_candidates(source_text, target_texts):
    """
    Rank target texts based on cosine similarity with the source text using ColBERTv2 multi-vector embeddings.
    
    Args:
        source_text (str): The source text to compare with target texts.
        target_texts (List[str]): List of target texts to rank.

    Returns:
        List[Tuple[int, float]]: List of (index, similarity score) sorted by similarity.
    """
    # Generate embeddings for the source text (multi-vector)
    source_embeddings = generate_embeddings(source_text)

    # Debug: Print the shape of the source embeddings
    print("Source embeddings shape:", source_embeddings.shape)

    # Generate embeddings for all target texts (multi-vector)
    target_embeddings = [generate_embeddings(target_text) for target_text in target_texts]

    # Compute similarity scores for each pair (source vs target)
    similarity_scores = []

    for target_embedding in target_embeddings:
        # Debug: Print the shape of the target embeddings
        print("Target embeddings shape:", target_embedding.shape)

        # Ensure source_embeddings and target_embedding have the expected shape
        if source_embeddings.dim() == 3:
            source_avg = torch.mean(source_embeddings, dim=1)  # Average over sequence length (dim=1)
        else:
            source_avg = source_embeddings  # If there's no sequence length, use the embeddings directly

        if target_embedding.dim() == 3:
            target_avg = torch.mean(target_embedding, dim=1)  # Average over sequence length (dim=1)
        else:
            target_avg = target_embedding  # If there's no sequence length, use the embeddings directly

        # Debug: Print the shapes after mean pooling
        print("Source_avg shape:", source_avg.shape)
        print("Target_avg shape:", target_avg.shape)

        # Add a batch dimension (unsqueeze(0)) to make them shape [1, hidden_size]
        source_avg = source_avg.unsqueeze(0)  # Shape: [1, hidden_size]
        target_avg = target_avg.unsqueeze(0)  # Shape: [1, hidden_size]

        # Debug: Check the shapes after unsqueeze
        print("Source_avg (after unsqueeze) shape:", source_avg.shape)
        print("Target_avg (after unsqueeze) shape:", target_avg.shape)

        # Compute cosine similarity between the average embeddings
        cos_sim = F.cosine_similarity(source_avg, target_avg)

        similarity_scores.append(cos_sim.item())

    # Rank candidates by similarity score
    ranked_indices = np.argsort(similarity_scores)[::-1]  # Sort in descending order
    return [(idx, similarity_scores[idx]) for idx in ranked_indices]

def rank_candidates_pytorch(source_embedding, target_embeddings):
    """
    Rank target embeddings based on cosine similarity to the source embedding.

    Args:
        source_embedding (torch.Tensor): The source embedding (1D Tensor).
        target_embeddings (torch.Tensor): The target embeddings (2D Tensor).

    Returns:
        List[Tuple[int, float]]: List of (index, similarity score) sorted by similarity.
    """
    # Compute cosine similarity in PyTorch
    similarities = torch.nn.functional.cosine_similarity(
        source_embedding.unsqueeze(0), target_embeddings, dim=1
    )

    # Rank candidates by similarity
    ranked_indices = torch.argsort(similarities, descending=True)
    return [(idx.item(), similarities[idx].item()) for idx in ranked_indices]

