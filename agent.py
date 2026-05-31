import os
import json
import subprocess
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

# Import existing tools from the user's scripts
from retrive_calendar_events import (
    add_google_calendar_event,
    get_upcoming_events,
    get_events_by_date_range,
    get_recently_updated_events
)
from notion_page_retrival import (
    add_notion_task as _add_notion_task,
    add_notion_note as _add_notion_note,
    append_notion_resource as _append_notion_resource,
    extract_page_content,
    extract_database_rows,
    NOTION_TARGETS
)
# ONLY importing the upcoming competitions helper, the scraper class is gone!
from competitive_programming_scrapper import get_upcoming_competitions

# Load environment variables
load_dotenv()

# ---------------------------------------------------------
# Coral Helper Function
# ---------------------------------------------------------
def execute_coral_query(query: str) -> str:
    """Helper to execute SQL queries directly against Coral."""
    print(f"\n[Coral Data Layer] Executing Query: {query}")
    try:
        result = subprocess.run(
            ["coral", "sql", query, "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing query: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

# ---------------------------------------------------------
# Wrap non-tool functions as Langchain tools
# ---------------------------------------------------------

@tool
def get_unscheduled_weak_topics() -> str:
    """
    Executes a Coral SQL JOIN across LeetCode stats and Google Calendar.
    Returns the top 5 weakest LeetCode topics that DO NOT currently have a study block scheduled.
    """
    query = """
    SELECT 
        l."tagName" AS weak_topic, 
        l."problemsSolved", 
        c.summary AS scheduled_block,
        c.start_date_time
    FROM 
        leetcode.topic_stats l
    LEFT JOIN 
        google_calendar.events c 
        ON c.summary ILIKE '%' || l."tagName" || '%'
    WHERE 
        l."problemsSolved" < 20
    ORDER BY 
        l."problemsSolved" ASC
    LIMIT 5;
    """
    return execute_coral_query(query)

@tool
def query_coral_database(sql_query: str) -> str:
    """
    Executes a custom SQL query against the Coral Unified Database.
    Available schemas: leetcode.topic_stats, codechef.profile, codeforces.profile, google_calendar.events
    """
    return execute_coral_query(sql_query)

@tool
def get_leetcode_stats(username: str) -> str:
    """Fetches topic-wise stats from LeetCode using the Coral Unified Data Layer."""
    query = 'SELECT "tagName", "problemsSolved" FROM leetcode.topic_stats ORDER BY "problemsSolved" ASC LIMIT 5;'
    return execute_coral_query(query)

@tool
def get_codechef_stats(username: str) -> str:
    """Fetches rating and rank statistics from CodeChef using the Coral Unified Data Layer."""
    query = 'SELECT username, current_rating, global_rank, stars FROM codechef.profile;'
    return execute_coral_query(query)

@tool
def get_codeforces_stats(username: str) -> str:
    """Fetches profile statistics from Codeforces using the Coral Unified Data Layer."""
    query = 'SELECT handle, rating, "maxRating", rank FROM codeforces.profile;'
    return execute_coral_query(query)

@tool
def add_notion_task(task_title: str) -> str:
    """Inserts a new task into the Notion Task List Board."""
    db_id = NOTION_TARGETS.get("Task List Board", {}).get("id")
    if not db_id or db_id == "YOUR_TRUE_DATABASE_ID_HERE":
        return "Error: Please set 'YOUR_TRUE_DATABASE_ID_HERE' in notion_page_retrival.py"
    
    print(f"\n[Notion Tool] Adding task: {task_title}")
    success = _add_notion_task(db_id, task_title)
    return "Task added successfully to Notion." if success else "Failed to add task to Notion."

@tool
def get_notion_page_content(page_id: str) -> str:
    """Extracts human-readable text from a Notion page."""
    return extract_page_content(page_id)

@tool
def append_notion_note(content: str) -> str:
    """Appends study materials and resources directly to the Notion Notes page."""
    page_id = NOTION_TARGETS.get("Notes", {}).get("id")
    if not page_id:
        return "Error: Could not find Notes page ID."
    
    print(f"\n[Notion Tool] Appending note to page {page_id}")
    success = _add_notion_note(page_id, content)
    return "Note added successfully to Notion." if success else "Failed to add note to Notion."

@tool
def append_notion_resource(title: str, url: str, is_video: bool = False) -> str:
    """Appends a sleek, clickable bookmark or embedded video directly to the Notion Notes page."""
    page_id = NOTION_TARGETS.get("Notes", {}).get("id")
    if not page_id:
        return "Error: Could not find Notes page ID."
    
    print(f"\n[Notion Tool] Appending resource '{title}' to page {page_id}")
    success = _append_notion_resource(page_id, title, url, is_video)
    return "Resource added successfully to Notion." if success else "Failed to add resource to Notion."

@tool
def get_upcoming_coding_competitions() -> str:
    """Fetches upcoming coding competitions from Codeforces, LeetCode, and CodeChef."""
    print("\n[Scraper Tool] Fetching upcoming competitions...")
    data = get_upcoming_competitions()
    return json.dumps(data, indent=2)

@tool
def web_search(query: str, search_type: str = "search") -> str:
    """Searches the web using the Serper API for articles or videos."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY is not set in .env."
        
    print(f"\n[Web Search] Query: '{query}' (Type: {search_type})")
    url = f"https://google.serper.dev/{search_type}"
    payload = json.dumps({"q": query, "num": 4})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        import requests
        response = requests.post(url, headers=headers, data=payload)
        data = response.json()
        
        results = []
        if search_type == "search" and "organic" in data:
            for item in data["organic"][:4]:
                results.append(f"- {item.get('title')}: {item.get('link')}")
        elif search_type == "videos" and "videos" in data:
            for item in data["videos"][:4]:
                results.append(f"- {item.get('title')}: {item.get('link')}")
                
        if not results:
            return "No results found."
        return "\n".join(results)
    except Exception as e:
        return f"Web search failed: {e}"


# ---------------------------------------------------------
# Agent Orchestration
# ---------------------------------------------------------

def get_agent():
    # Initialize the OpenRouter model
    llm = ChatOpenAI(
        api_key=os.environ.get("OPENROUTER_API_KEY", "dummy"),
        base_url="https://openrouter.ai/api/v1",
        model="nvidia/nemotron-3-super-120b-a12b:free"
    )
    
    tools = [
        add_google_calendar_event,
        get_upcoming_events,
        get_events_by_date_range,
        get_recently_updated_events,
        add_notion_task,
        get_notion_page_content,
        get_leetcode_stats,
        get_codechef_stats,
        get_codeforces_stats,
        query_coral_database,
        append_notion_note,
        append_notion_resource,
        get_upcoming_coding_competitions,
        web_search
        get_unscheduled_weak_topics
    ]
    
    leetcode_username = os.getenv("LEETCODE_USERNAME", "notaceninja")
    codechef_username = os.getenv("CODECHEF_USERNAME", "notaceninja")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "pushkarsharma.rtm@gmail.com")
    
    system_message = f"""You are 'The Grandmaster’s Ledger', an autonomous AI training officer.
Your goal is to optimize an engineer's competitive programming and technical interview roadmap.

USER CONTEXT:
- LeetCode Username: {leetcode_username}
- CodeChef Username: {codechef_username}
- Google Calendar ID: {calendar_id}

CORAL DATA STRATEGY (CRITICAL):
You are backed by the Coral Unified Data Engine. You must use `get_leetcode_stats`, `get_codechef_stats`, and `get_codeforces_stats` to query algorithmic weak spots directly via SQL. 
If you need to perform an advanced cross-platform check, use the `query_coral_database` tool to execute a JOIN. For example:
SELECT l."tagName", l."problemsSolved", c.summary FROM leetcode.topic_stats l LEFT JOIN google_calendar.events c ON c.summary ILIKE '%' || l."tagName" || '%' WHERE l."problemsSolved" < 15 ORDER BY l."problemsSolved" ASC LIMIT 5;

ACTION PROTOCOL:
1. Fetch stats and upcoming contests via Coral tools.
2. Schedule EXACT contests on their Google Calendar using `start_time_utc`.
3. Schedule MULTIPLE focus blocks TODAY to cover the weakest topics found in the database.
4. Add those study topics as tasks in Notion using `add_notion_task`.
5. Use `web_search` to find real articles, exact LeetCode problems, and YouTube video tutorials for the weak topics.
6. Push the discovered links to Notion using `append_notion_resource` (set `is_video=True` for YouTube).
Respond directly to the user after taking actions, summarizing the strategy.
"""
    
    agent_executor = create_agent(llm, tools, system_prompt=system_message)
    return agent_executor

if __name__ == "__main__":
    agent = get_agent()
    print("🤖 The Grandmaster's Ledger is online.")
    print("💡 Tip: You can paste multiple lines. Press Enter on an EMPTY line to send your message.\n")
    
    while True:
        try:
            print("You: ")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
                
            user_input = "\n".join(lines).strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                print("\nShutting down The Grandmaster's Ledger...")
                break
                
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            for chunk in agent.stream(inputs, stream_mode="values"):
                message = chunk["messages"][-1]
                if message.type == "ai" and message.content:
                    print(f"\nAgent: {message.content}\n")
                elif message.type == "tool":
                    print(f"Tool returned: {message.content[:200]}...")
                    
        except KeyboardInterrupt:
            print("\nShutting down The Grandmaster's Ledger...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")