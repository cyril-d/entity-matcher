import openai

# Set your OpenAI API key
openai.api_key = "your_openai_api_key_here"

def query_llm(source_field, target_fields):
    """Queries an LLM to find the best matches."""
    prompt = f"Match the following field to its best corresponding field:\nSource: {source_field}\nTargets: {', '.join(target_fields)}\nProvide matches ranked by relevance."
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip().split("\n")
