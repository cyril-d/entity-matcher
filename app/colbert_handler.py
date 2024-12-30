from transformers import AutoTokenizer, AutoModel
import torch

INDEX_DIR = "./colbert_index"
MODEL_NAME = "bert-base-uncased"

# Load the ColBERTv2 model and tokenizer globally (to avoid reloading them repeatedly)
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")  # Replace with ColBERTv2 tokenizer if different
model = AutoModel.from_pretrained("bert-base-uncased")          # Replace with ColBERTv2 model if different
model.eval()  # Set model to evaluation mode

def embed_text(text):
    """
    Generate an embedding for the given text using ColBERTv2 or another model.

    Args:
        text (str): The text to embed.

    Returns:
        torch.Tensor: The embedding for the input text.
    """
    with torch.no_grad():
        # Tokenize the input text
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
        
        # Generate embeddings
        outputs = model(**inputs)
        
        # Use the [CLS] token representation as the embedding (common practice)
        embedding = outputs.last_hidden_state[:, 0, :]  # [batch_size, hidden_dim]

        return embedding.squeeze(0)  # Remove batch dimension

def embed_text_batch(texts):
    inputs = tokenizer(texts, return_tensors="pt", truncation=True, padding=True)
    outputs = model(**inputs)
    embeddings = outputs.last_hidden_state[:, 0, :]  # Use [CLS] token for each input
    return embeddings  # Shape: [batch_size, hidden_dim]
