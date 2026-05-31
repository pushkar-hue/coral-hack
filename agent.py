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
    extract_page_content,
    extract_database_rows,
    NOTION_TARGETS
)
from competitive_programming_scrapper import CompetitiveProgrammingScraper, get_upcoming_competitions

# Load environment variables
load_dotenv()

# ---------------------------------------------------------
# Wrap non-tool functions as Langchain tools
# ---------------------------------------------------------

@tool
def add_notion_task(task_title: str) -> str:
    """
    Inserts a new task into the Notion Task List Board.
    """
    db_id = NOTION_TARGETS.get("Task List Board", {}).get("id")
    if not db_id or db_id == "YOUR_TRUE_DATABASE_ID_HERE":
        return "Error: Please set 'YOUR_TRUE_DATABASE_ID_HERE' in notion_page_retrival.py under NOTION_TARGETS['Task List Board']['id']"
    
    print(f"\n[Notion Tool] Adding task: {task_title}")
    success = _add_notion_task(db_id, task_title)
    return "Task added successfully to Notion." if success else "Failed to add task to Notion."

@tool
def get_notion_page_content(page_id: str) -> str:
    """
    Extracts human-readable text from a Notion page. 
    Use id '36dac41d8487809c9f36e36667295344' for Notes or 'ab107fc93e23451584e88751e9996143' for Student Dashboard.
    """
    return extract_page_content(page_id)

@tool
def get_leetcode_stats(username: str) -> str:
    """Fetches general stats AND topic-wise stats from LeetCode."""
    scraper = CompetitiveProgrammingScraper(username)
    data = scraper.get_leetcode_data()
    return json.dumps(data)

@tool
def get_codechef_stats(username: str) -> str:
    """Scrapes rating and rank statistics from CodeChef."""
    scraper = CompetitiveProgrammingScraper(username)
    data = scraper.get_codechef_stats()
    return json.dumps(data)

@tool
def append_notion_note(content: str) -> str:
    """
    Appends study materials and resources directly to the Notion Notes page.
    """
    page_id = NOTION_TARGETS.get("Notes", {}).get("id")
    if not page_id:
        return "Error: Could not find Notes page ID."
    
    print(f"\n[Notion Tool] Appending note to page {page_id}")
    success = _add_notion_note(page_id, content)
    return "Note added successfully to Notion." if success else "Failed to add note to Notion."

@tool
def get_upcoming_coding_competitions() -> str:
    """Fetches upcoming coding competitions from Codeforces, LeetCode, and CodeChef."""
    print("\n[Scraper Tool] Fetching upcoming competitions...")
    data = get_upcoming_competitions()
    return json.dumps(data, indent=2)

@tool
def query_coral_database(sql_query: str) -> str:
    """
    Executes a SQL query against the Coral Unified Database.
    Schema includes: leetcode_profile, leetcode_topics, codechef_profile, notion_syllabus, calendar_events.
    """
    print(f"\n[Coral Tool] Executing Query: {sql_query}")
    try:
        result = subprocess.run(
            ["coral", "sql", sql_query, "--format", "json"],
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
# Agent Orchestration
# ---------------------------------------------------------

def get_agent():
    # Initialize the OpenRouter model with the user's requested model string
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
        query_coral_database,
        append_notion_note,
        get_upcoming_coding_competitions
    ]
    
    leetcode_username = os.getenv("LEETCODE_USERNAME", "notaceninja")
    codechef_username = os.getenv("CODECHEF_USERNAME", "notaceninja")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "pushkarsharma.rtm@gmail.com")
    
    system_message = f"""You are 'The Grandmaster’s Ledger', an autonomous AI training officer.
Your goal is to optimize an engineer's competitive programming and technical interview roadmap.

USER CONTEXT (DO NOT ASK FOR THESE, USE THEM AUTOMATICALLY):
- LeetCode Username: {leetcode_username}
- CodeChef Username: {codechef_username}
- Google Calendar ID: {calendar_id}

You have access to the following tools to get data and perform actions:
- `get_leetcode_stats` / `get_codechef_stats` to analyze programming profiles.
- `get_notion_page_content` to review their notes/syllabus (use Notes ID: 36dac41d8487809c9f36e36667295344, Student Dashboard ID: ab107fc93e23451584e88751e9996143).
- `get_upcoming_coding_competitions` to fetch upcoming coding contests from Codeforces, LeetCode, and CodeChef.
- `get_upcoming_events` / `get_events_by_date_range` to check their Google Calendar.
- `add_notion_task` to assign specific high-yield problems or topics to study.
- `append_notion_note` to add useful resource material and learning notes directly to their Notion Notes. (IMPORTANT: When adding study material, you MUST include clickable YouTube search links, e.g. `[Watch Segment Tree Tutorial](https://www.youtube.com/results?search_query=Segment+Tree+tutorial)`).
- `add_google_calendar_event` to block out focus time or schedule upcoming competitions on their calendar. You can schedule multiple blocks TODAY using the `start_time_utc` parameter (e.g., '2026-05-31T15:00:00Z') and `duration_hours`.
- `query_coral_database` to run a unified SQL query across all data sources simultaneously if needed.

When a user asks for a schedule or analysis:
1. Fetch their stats and find weak points.
2. Fetch upcoming contests and ACTUALY SCHEDULE those exact contests on their Google Calendar using `start_time_utc`.
3. Schedule MULTIPLE focus blocks starting TODAY to cover the weak points using `start_time_utc`.
4. Add those study topics as tasks in Notion using `add_notion_task`.
5. Append YouTube search links and study material to Notion using `append_notion_note`.
Respond directly to the user after taking actions, summarizing the strategy and the actions taken.
"""
    
    agent_executor = create_agent(llm, tools, system_prompt=system_message)
    return agent_executor

if __name__ == "__main__":
    agent = get_agent()
    print("🤖 The Grandmaster's Ledger is online. (Type 'exit' to quit)\n")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            # Using standard stream output
            for chunk in agent.stream(inputs, stream_mode="values"):
                message = chunk["messages"][-1]
                if message.type == "ai" and message.content:
                    print(f"Agent: {message.content}")
                elif message.type == "tool":
                    print(f"Tool returned: {message.content[:200]}...")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")
