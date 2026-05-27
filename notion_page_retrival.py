import subprocess
import json

# Your 5 discovered Notion IDs mapped by their type
NOTION_TARGETS = {
    "Notes": {
        "id": "36dac41d8487809c9f36e36667295344",
        "type": "page"
    },
    "Student Dashboard": {
        "id": "ab107fc93e23451584e88751e9996143",
        "type": "page"
    }
}

def execute_coral_query(query):
    """Executes a Coral SQL query and returns the parsed JSON result."""
    try:
        # We use --format json so Python can parse it instead of the ASCII table
        result = subprocess.run(
            ["coral", "sql", query, "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Coral Query Failed: {e.stderr}")
        return []
    except json.JSONDecodeError:
        print("Failed to parse JSON. Ensure Coral supports the --format json flag.")
        return []

def extract_page_content(page_id):
    """Extracts human-readable text from a standard Notion page."""
    query = f"SELECT type, raw FROM notion.block_children WHERE block_id = '{page_id}';"
    rows = execute_coral_query(query)
    
    clean_text = []
    for row in rows:
        block_type = row.get("type")
        raw_data = json.loads(row.get("raw", "{}"))
        
        if block_type in raw_data and "rich_text" in raw_data[block_type]:
            text_segments = [
                segment.get("plain_text", "") 
                for segment in raw_data[block_type]["rich_text"]
            ]
            clean_text.append("".join(text_segments))
            
    return "\n".join(clean_text)

def extract_database_rows(db_id):
    """Extracts the properties (columns) for every row in a Notion database."""
    query = f"SELECT id, properties FROM notion.data_source_pages WHERE data_source_id = '{db_id}';"
    rows = execute_coral_query(query)
    
    parsed_rows = []
    for row in rows:
        # The 'properties' column contains the raw JSON of the database fields
        properties = json.loads(row.get("properties", "{}"))
        row_data = {"page_id": row.get("id")}
        
        # Simplify the nested Notion property JSON into a flat dictionary
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            # Handle common Notion database property types
            if prop_type == "title" and prop_data["title"]:
                row_data[prop_name] = prop_data["title"][0].get("plain_text", "")
            elif prop_type == "rich_text" and prop_data["rich_text"]:
                row_data[prop_name] = prop_data["rich_text"][0].get("plain_text", "")
            elif prop_type == "select" and prop_data["select"]:
                row_data[prop_name] = prop_data["select"].get("name", "")
            elif prop_type == "status" and prop_data["status"]:
                row_data[prop_name] = prop_data["status"].get("name", "")
            
        parsed_rows.append(row_data)
        
    return parsed_rows

def main():
    print("🚢 Setting sail! Fetching all Notion targets...\n")
    
    for name, metadata in NOTION_TARGETS.items():
        print(f"--- Fetching {name} ({metadata['type'].upper()}) ---")
        
        if metadata["type"] == "page":
            content = extract_page_content(metadata["id"])
            print(f"Preview: {content[:150]}...\n")
            
        elif metadata["type"] == "database":
            rows = extract_database_rows(metadata["id"])
            print(f"Found {len(rows)} entries.")
            if rows:
                print(f"First entry preview: {rows[0]}\n")
            else:
                print("\n")

if __name__ == "__main__":
    main()