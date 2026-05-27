import subprocess
import json
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool

# ---------------------------------------------------------
# Helper: Fetch All Events (Clean Query)
# ---------------------------------------------------------
def _fetch_all_events(calendar_id: str) -> list:
    """
    Internal helper to fetch all events for a calendar without filters.
    Returns list of events or empty list on error.
    """
    query = f"SELECT summary, description, updated FROM google_calendar.events WHERE calendar_id = '{calendar_id}';"
    
    try:
        result = subprocess.run(
            ["coral", "sql", query, "--format", "json"],
            capture_output=True, text=True, check=False
        )
        
        if not result.stdout or not result.stdout.strip():
            return []
        
        return json.loads(result.stdout)
    except:
        return []

# ---------------------------------------------------------
# Tool 1: Date Range Explorer
# ---------------------------------------------------------
@tool
def get_events_by_date_range(calendar_id: str, start_date: str, end_date: str) -> str:
    """
    Fetches calendar events strictly between a start_date and end_date.
    Use this when the user asks about a specific week, month, or exact timeframe.
    
    Args:
        calendar_id: The target Google Calendar email.
        start_date: The beginning date in 'YYYY-MM-DD' format (e.g., '2026-05-27').
        end_date: The ending date in 'YYYY-MM-DD' format (e.g., '2026-05-31').
    """
    
    try:
        events = _fetch_all_events(calendar_id)
        
        if not events:
            return f"No events found between {start_date} and {end_date}."
        
        # Filter events by date range locally (using updated field)
        filtered = []
        for e in events:
            updated = e.get('updated', '')[:10]  # Extract YYYY-MM-DD from timestamp
            if updated and start_date <= updated <= end_date:
                filtered.append(e)
        
        if not filtered:
            return f"No events found between {start_date} and {end_date}."
            
        formatted = [f"--- Events from {start_date} to {end_date} ---"]
        for e in filtered:
            formatted.append(f"• {e.get('updated', 'Unknown Date')}: {e.get('summary', 'Untitled')}")
        return "\n".join(formatted)

    except Exception as e:
        return f"Tool Error: {str(e)}"

# ---------------------------------------------------------
# Tool 2: Upcoming Events (From Today Onward)
# ---------------------------------------------------------
@tool
def get_upcoming_events(calendar_id: str) -> str:
    """
    Fetches upcoming calendar events from today onward.
    Use this for checking your schedule for the next few days.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    try:
        events = _fetch_all_events(calendar_id)
        
        if not events:
            return "No upcoming events found from today onward."
        
        # Filter events from today onward locally (using updated field)
        upcoming = []
        for e in events:
            updated = e.get('updated', '')[:10]  # Extract YYYY-MM-DD from timestamp
            if updated and updated >= today:
                upcoming.append(e)
        
        if not upcoming:
            return "No upcoming events found from today onward."
            
        formatted = ["--- Upcoming Events ---"]
        for e in upcoming:
            formatted.append(f"• {e.get('updated', 'Unknown Date')}: {e.get('summary', 'Untitled')}")
        return "\n".join(formatted)
        
    except Exception as e:
        return f"Tool Execution Error: {str(e)}"
        
# ---------------------------------------------------------
# Tool 3: The Bulletproof Fallback (Recently Updated)
# ---------------------------------------------------------
@tool
def get_recently_updated_events(calendar_id: str) -> str:
    """
    Fetches the 5 most recently created or updated events in the calendar.
    CRITICAL: Use this if the date-based tools return empty, as time-bound events sometimes bypass date filters.
    """
    query = f"SELECT summary, updated FROM google_calendar.events WHERE calendar_id = '{calendar_id}' ORDER BY updated DESC LIMIT 5;"
    
    try:
        result = subprocess.run(
            ["coral", "sql", query, "--format", "json"],
            capture_output=True, text=True, check=False
        )
        events = json.loads(result.stdout)
        
        if not events:
            return "No recently updated events found."
            
        formatted = ["--- Recently Modified Events (Time-Bound Safe) ---"]
        for e in events:
            formatted.append(f"• {e.get('summary', 'Untitled')} (Updated: {e.get('updated', 'Unknown')})")
        return "\n".join(formatted)

    except Exception as e:
        return f"Tool Error: {str(e)}"

def main():
    """
    Main function to orchestrate and test all tools sequentially.
    """
    # Replace with your actual email and page ID
    TARGET_EMAIL = "pushkarsharma.rtm@gmail.com"
    NOTION_PAGE_ID = "36dac41d8487809c9f36e36667295344"
    
    print("🚀 Starting Tool Test Suite...\n")
    
    # 1. Test Upcoming Events
    print(f"--- Testing: Upcoming Events for {TARGET_EMAIL} ---")
    print(get_upcoming_events.invoke({"calendar_id": TARGET_EMAIL}))
    print("\n")
    
    # 2. Test Range-based Query (e.g., this week)
    print("--- Testing: Date Range Query (Next 7 Days) ---")
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    print(get_events_by_date_range.invoke({
        "calendar_id": TARGET_EMAIL, 
        "start_date": start, 
        "end_date": end
    }))
    print("\n")
    
    # 3. Test Recently Updated (The "Panic-Safe" Fallback)
    print("--- Testing: Recently Updated Events ---")
    print(get_recently_updated_events.invoke({"calendar_id": TARGET_EMAIL}))
    print("\n")
    
    # 4. Test Notion Content
    print(f"--- Testing: Notion Content Retrieval ---")
    print(fetch_notion_notes.invoke({"page_id": NOTION_PAGE_ID}))

if __name__ == "__main__":
    main()