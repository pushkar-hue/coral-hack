import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

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

def add_notion_markdown_note(page_id, md_text):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    children = []
    lines = md_text.split('\n')
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
        
    payload = {"children": children}
    response = requests.patch(url, headers=NOTION_HEADERS, json=payload)
    print(response.status_code, response.text[:100])

sample_md = """## Segment Tree
- Watch [Segment Tree Tutorial](https://youtube.com)
- Read [GeeksForGeeks Article](https://geeksforgeeks.org)
- Solve [LeetCode 307](https://leetcode.com/problems/range-sum-query-mutable/)"""

add_notion_markdown_note("36dac41d8487809c9f36e36667295344", sample_md)
