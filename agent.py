import os
import json
import subprocess
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Import existing tools from the user's scripts
from retrive_calendar_events import (
    add_google_calendar_event,
    get_upcoming_events,
    get_events_by_date_range,
    get_recently_updated_events
)
from notion_page_retrival import (
    add_notion_task as _add_notion_task,
    extract_page_content,
    extract_database_rows,
    NOTION_TARGETS
)
from competitive_programming_scrapper import CompetitiveProgrammingScraper

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
        model="openai/gpt-oss-120b:free"
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
        query_coral_database
    ]
    
    system_message = """You are 'The Grandmaster’s Ledger', an autonomous AI training officer.
Your goal is to optimize an engineer's competitive programming and technical interview roadmap.

You have access to the following tools to get data and perform actions:
- `get_leetcode_stats` / `get_codechef_stats` to analyze programming profiles.
- `get_notion_page_content` to review their notes/syllabus (use Notes ID: 36dac41d8487809c9f36e36667295344, Student Dashboard ID: ab107fc93e23451584e88751e9996143).
- `get_upcoming_events` / `get_events_by_date_range` to check their Google Calendar.
- `add_notion_task` to assign specific high-yield problems or topics to study.
- `add_google_calendar_event` to block out focus time on their calendar.
- `query_coral_database` to run a unified SQL query across all data sources simultaneously if needed.

When a user asks for a schedule or analysis, fetch their data, analyze their weak points, and use the action tools (`add_notion_task`, `add_google_calendar_event`) to schedule their training. Respond directly to the user after taking actions, summarizing the strategy and the actions taken.
"""
    
    agent_executor = create_react_agent(llm, tools, state_modifier=system_message)
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
