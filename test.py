import torch
from sentence_transformers import SentenceTransformer
config = {
    "models": [
        {"name": "openai", "use": lambda api_key: bool(api_key)},
        {"name": "multi-qa-mpnet-base-dot-v1", "instance": SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")},
    ],
}
model_name = "multi-qa-mpnet-base-dot-v1"
model = next((x["instance"] for x in config["models"] if x["name"] == model_name), None)
text = "Field: putType. Description: Put option type. Values include: 'A' American, 'B' Bermudan, 'E' European, 'S' Asian. Full list of valid values are in the CALL_PUT_TYPE decode."
embedding = model.encode([text], convert_to_tensor=True)[0]
print(embedding)
