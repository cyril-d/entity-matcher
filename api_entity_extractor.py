import yaml
import requests
import sys
from app.database import insert_or_update_schema, insert_or_update_entity, db


def download_spec_from_url(url):
    """
    Downloads an OpenAPI/Swagger specification from a given URL.

    Args:
        url (str): The URL to fetch the spec from.

    Returns:
        dict: The parsed YAML/JSON content of the specification.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Attempt to parse as YAML or JSON
        return yaml.safe_load(response.text)

    except Exception as e:
        print(f"Error downloading or parsing spec from {url}: {e}")
        return None


def extract_entities_from_spec(spec):
    """
    Extracts entities from OpenAPI or Swagger specifications.
    Entities are objects that have at least one primitive or enum property (leaf node).
    
    Args:
        spec (dict): Parsed OpenAPI or Swagger specification.
    
    Returns:
        list: A list of dictionaries containing entity names and their fields.
    """
    entities = []

    # Locate schemas or definitions (depending on OpenAPI/Swagger version)
    schemas = spec.get("components", {}).get("schemas", {})
    if not schemas:
        schemas = spec.get("definitions", {})

    for schema_name, schema in schemas.items():
        # Ensure this schema is an object with properties
        schema_type = schema.get("type")
        properties = schema.get("properties", {})
        if schema_type != "object" or not properties:
            continue

        # Collect fields (leaf properties) and determine if it has primitives
        fields = []
        has_primitive = False
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type")

            # Check if the property is a reference to another object
            if prop_type == "object" and "$ref" in prop_info:
                continue  # Skip, as it's a reference

            if prop_type == "array" and "items" in prop_info and "$ref" in prop_info["items"]:
                continue  # Skip, as it's an array of references

            # If it's a primitive or enum, add it to fields
            if prop_type in ["string", "number", "boolean", "integer"]:
                has_primitive = True
                fields.append({
                    "name": prop_name,
                    "description": prop_info.get("description", ""),
                    "type": prop_type,
                })
            elif "enum" in prop_info:
                has_primitive = True
                fields.append({
                    "name": prop_name,
                    "description": prop_info.get("description", ""),
                    "type": "enum",
                    "enum": prop_info["enum"]
                })

        # If it has at least one primitive property, treat it as an entity
        if has_primitive:
            entities.append({
                "name": schema_name,
                "description": schema.get("description", ""),
                "fields": fields
            })

    return entities

def process_sources(input_file, schema_name, schema_description):
    """
    Reads a list of OpenAPI/Swagger YAML file paths or URLs, extracts entities, 
    and inserts them into the database under a single schema.

    Args:
        input_file (str): Path to the file containing OpenAPI/Swagger sources (file paths or URLs).
        schema_name (str): Name of the schema to insert entities into.
        schema_description (str): Description of the schema.
    """
    # Create or update the schema in the database
    schema = insert_or_update_schema(schema_name, schema_description)

    try:
        # Read the list of sources (file paths or URLs)
        with open(input_file, 'r') as file:
            sources = [
                line.strip()
                for line in file.readlines()
                if line.strip() and not line.strip().startswith("#")
            ]

        if not sources:
            print("No sources found in the input file.")
            return

        print(f"Processing schema: {schema_name} (ID: {schema.id})")

        # Loop through each source and extract entities
        for source in sources:
            print(f"Processing source: {source}")

            # Determine if the source is a URL or a file path
            if source.startswith("http://") or source.startswith("https://"):
                spec = download_spec_from_url(source)
            else:
                try:
                    with open(source, 'r') as file:
                        spec = yaml.safe_load(file)
                except Exception as e:
                    print(f"Error reading or parsing file {source}: {e}")
                    spec = None

            if not spec:
                print(f"Skipping invalid or unreadable source: {source}")
                continue

            # Extract entities from the specification
            entities = extract_entities_from_spec(spec)

            if not entities:
                print(f"No entities found in source: {source}")
                continue

            # Insert or update each entity in the database
            for entity in entities:
                entity_name = entity.get('name')
                entity_description = entity.get('description')

                insert_or_update_entity(
                    schema_id=schema.id,
                    entity_name=entity_name,
                    entity_description=entity_description,
                    fields_data=[]  # Empty since OpenAPI/Swagger entities typically don't have fields directly
                )

                print(f"Inserted/Updated entity: {entity_name}")

        print("All sources processed successfully.")

    except Exception as e:
        print(f"Error processing sources: {e}")


if __name__ == "__main__":
    # Command-line arguments
    if len(sys.argv) != 4:
        print("Usage: python api_entity_extractor.py <input_file> <schema_name> <schema_description>")
        sys.exit(1)

    input_file = sys.argv[1]
    schema_name = sys.argv[2]
    schema_description = sys.argv[3]

    # Initialize Flask app context for database operations
    from app import app  # Import the Flask app

    with app.app_context():
        process_sources(input_file, schema_name, schema_description)

# Sample File: sources.txt
