import re

def parse_md_to_rich_text(text):
    rich_text = []
    # Split by markdown links: [text](url)
    parts = re.split(r'\[(.*?)\]\((.*?)\)', text)
    
    # The split returns: [text_before, link_text, link_url, text_after, ...]
    # So every 3rd element starting from 0 is normal text.
    # index 1 is link_text, index 2 is link_url.
    
    i = 0
    while i < len(parts):
        # Normal text
        if parts[i]:
            rich_text.append({
                "type": "text",
                "text": {"content": parts[i]}
            })
        
        # If there is a link following
        if i + 2 < len(parts):
            link_text = parts[i+1]
            link_url = parts[i+2]
            rich_text.append({
                "type": "text",
                "text": {
                    "content": link_text,
                    "link": {"url": link_url}
                }
            })
        i += 3
        
    return rich_text

print(parse_md_to_rich_text("Watch [this tutorial](https://youtube.com) and [this problem](https://leetcode.com). Done!"))
