import os
import subprocess
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")

# Standard Notion API Headers
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Your discovered Notion IDs mapped by their type
NOTION_TARGETS = {
    "Notes": {
        "id": "36dac41d8487809c9f36e36667295344",
        "type": "page"
    },
    "Student Dashboard": {
        "id": "ab107fc93e23451584e88751e9996143",
        "type": "page"
    },
    "Task List Board": {
        "id": "7ef8808dc3a54831879d6dcbcf15c188",
        "type": "database"
    }
}

def execute_coral_query(query):
    """Executes a Coral SQL query and returns the parsed JSON result."""
    try:
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
    """Extracts human-readable text from a standard Notion page using Coral."""
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
    """Extracts the properties (columns) for every row in a Notion database via Direct API."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    
    response = requests.post(url, headers=NOTION_HEADERS)
    
    if response.status_code != 200:
        print(f"❌ API Error fetching database: {response.text}")
        return []

    results = response.json().get("results", [])
    parsed_rows = []
    
    for row in results:
        row_data = {"page_id": row.get("id")}
        properties = row.get("properties", {})
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            
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

def add_notion_task(db_id, task_title, title_column_name="Name"):
    """
    Inserts a new row (task) into a Notion database via Direct API.
    """
    url = "https://api.notion.com/v1/pages"
    
    payload = {
        "parent": {
            "database_id": db_id
        },
        "properties": {
            title_column_name: {
                "title": [
                    {
                        "text": {
                            "content": task_title
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": "To Do"
                }
            }
        }
    }
    
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    
    if response.status_code == 200:
        print(f"✅ Successfully added task: '{task_title}'")
        return True
    else:
        print(f"❌ Failed to add task. API Error: {response.text}")
        return False

import re

def parse_md_to_rich_text(text):
    rich_text = []
    parts = re.split(r'\[(.*?)\]\((.*?)\)', text)
    i = 0
    while i < len(parts):
        if parts[i]:
            rich_text.append({"type": "text", "text": {"content": parts[i]}})
        if i + 2 < len(parts):
            rich_text.append({
                "type": "text",
                "text": {"content": parts[i+1], "link": {"url": parts[i+2]}}
            })
        i += 3
    return rich_text

def add_notion_note(page_id, text_content):
    """
    Appends markdown-formatted text blocks to a Notion page.
    Supports basic paragraphs, heading_2 (##), heading_3 (###), and bulleted_list_item (- or *).
    Also parses [text](url) links into rich_text links.
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    children = []
    lines = text_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        block = {"object": "block"}
        
        if line.startswith("## "):
            block["type"] = "heading_2"
            block["heading_2"] = {"rich_text": parse_md_to_rich_text(line[3:].strip())}
        elif line.startswith("### "):
            block["type"] = "heading_3"
            block["heading_3"] = {"rich_text": parse_md_to_rich_text(line[4:].strip())}
        elif line.startswith("- ") or line.startswith("* "):
            block["type"] = "bulleted_list_item"
            block["bulleted_list_item"] = {"rich_text": parse_md_to_rich_text(line[2:].strip())}
        else:
            block["type"] = "paragraph"
            block["paragraph"] = {"rich_text": parse_md_to_rich_text(line)}
            
        children.append(block)
        
    # Send chunks of 100 blocks at most
    for i in range(0, len(children), 100):
        chunk = children[i:i+100]
        payload = {"children": chunk}
        response = requests.patch(url, headers=NOTION_HEADERS, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Failed to append note. API Error: {response.text}")
            return False
            
    print(f"✅ Successfully appended note to page {page_id}")
    return True

def append_notion_resource(page_id: str, title: str, url: str, is_video: bool = False):
    """Appends a sleek, clickable bookmark or embedded video to the Notion page."""
    
    block_type = "video" if is_video else "bookmark"
    block_content = {
        "type": "external",
        "external": { "url": url }
    } if is_video else { "url": url }

    payload = {
        "children": [
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": title}}]
                }
            },
            {
                "object": "block",
                "type": block_type,
                block_type: block_content
            }
        ]
    }
    
    patch_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = requests.patch(patch_url, headers=NOTION_HEADERS, json=payload)
    if response.status_code == 200:
        print(f"✅ Successfully appended resource '{title}' to page {page_id}")
        return True
    else:
        print(f"❌ Failed to append resource. API Error: {response.text}")
        return False

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