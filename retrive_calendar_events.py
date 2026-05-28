import os
import subprocess
import json
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool

# Google API Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# ---------------------------------------------------------
# Auth Engine: Persistent OAuth2 Flow (For Writes)
# ---------------------------------------------------------
def get_calendar_service():
    """Authenticates the user and builds the Calendar API service for reliable writes."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("Missing 'credentials.json'. Download it from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

# ---------------------------------------------------------
# Helper: Execute Coral Query (For Reads)
# ---------------------------------------------------------
def execute_coral_query(query: str):
    """Executes a Coral read query, ignoring Tokio noise."""
    try:
        result = subprocess.run(
            ["coral", "sql", query, "--format", "json"],
            capture_output=True, text=True, check=False 
        )
        
        if not result.stdout or not result.stdout.strip():
            return []
            
        return json.loads(result.stdout)
    except Exception as e:
        print(f"[DEBUG] Python Execution Error: {str(e)}")
        return []

# ---------------------------------------------------------
# Tool 1: Insert Event (Google API)
# ---------------------------------------------------------
@tool
def add_google_calendar_event(calendar_id: str, summary: str, description: str = "", hours_from_now: int = 1) -> str:
    """Creates a new 1-hour event in Google Calendar using the official REST API."""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=hours_from_now)
    end_time = start_time + timedelta(hours=1)
    
    event_payload = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'timeZone': 'UTC',
        },
    }
    
    try:
        service = get_calendar_service()
        event = service.events().insert(calendarId=calendar_id, body=event_payload).execute()
        return f"✅ Successfully scheduled '{summary}'. View here: {event.get('htmlLink')}"
    except Exception as e:
        return f"❌ Insert Failed: {str(e)}"

# ---------------------------------------------------------
# Tool 2: Upcoming Events (Coral SQL)
# ---------------------------------------------------------
@tool
def get_upcoming_events(calendar_id: str) -> str:
    """Fetches upcoming calendar events from today onward."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    
    query = f"""
    SELECT summary, start_date_time 
    FROM google_calendar.events 
    WHERE calendar_id = '{calendar_id}' 
      AND start_date_time >= CAST('{today}' AS TIMESTAMP)
    ORDER BY start_date_time ASC
    LIMIT 10;
    """
    
    events = execute_coral_query(query)
    
    if not events:
        return "No upcoming events found from today onward."
        
    formatted = ["--- Upcoming Events ---"]
    for e in events:
        dt = e.get('start_date_time', 'Unknown')
        clean_dt = dt[:16].replace('T', ' ') if dt != 'Unknown' else dt
        formatted.append(f"• {clean_dt}: {e.get('summary', 'Untitled')}")
        
    return "\n".join(formatted)

# ---------------------------------------------------------
# Tool 3: Date Range Explorer (Coral SQL)
# ---------------------------------------------------------
@tool
def get_events_by_date_range(calendar_id: str, start_date: str, end_date: str) -> str:
    """Fetches calendar events strictly between a start_date and end_date (YYYY-MM-DD)."""
    start_ts = f"{start_date}T00:00:00Z"
    end_ts = f"{end_date}T23:59:59Z"
    
    query = f"""
    SELECT summary, start_date_time 
    FROM google_calendar.events 
    WHERE calendar_id = '{calendar_id}' 
      AND start_date_time >= CAST('{start_ts}' AS TIMESTAMP) 
      AND start_date_time <= CAST('{end_ts}' AS TIMESTAMP)
    ORDER BY start_date_time ASC;
    """
    
    events = execute_coral_query(query)
    
    if not events:
        return f"No events found between {start_date} and {end_date}."
        
    formatted = [f"--- Events from {start_date} to {end_date} ---"]
    for e in events:
        dt = e.get('start_date_time', 'Unknown')
        clean_dt = dt[:16].replace('T', ' ') if dt != 'Unknown' else dt
        formatted.append(f"• {clean_dt}: {e.get('summary', 'Untitled')}")
        
    return "\n".join(formatted)

# ---------------------------------------------------------
# Tool 4: Recently Updated (Coral SQL)
# ---------------------------------------------------------
@tool
def get_recently_updated_events(calendar_id: str) -> str:
    """Fetches the 5 most recently created or updated events."""
    query = f"""
    SELECT summary, updated 
    FROM google_calendar.events 
    WHERE calendar_id = '{calendar_id}' 
    ORDER BY updated DESC 
    LIMIT 5;
    """
    
    events = execute_coral_query(query)
    
    if not events:
        return "No recently updated events found."
        
    formatted = ["--- Top 5 Recently Modified Events ---"]
    for e in events:
        dt = e.get('updated', 'Unknown')
        clean_dt = dt[:16].replace('T', ' ') if dt != 'Unknown' else dt
        formatted.append(f"• {e.get('summary', 'Untitled')} (Updated: {clean_dt})")
        
    return "\n".join(formatted)


def main():
    TARGET_EMAIL = "pushkarsharma.rtm@gmail.com"

    print("🚀 Starting Hybrid Architecture Test Suite...\n")
    
    print("🗓️ Testing Google REST API Insert Operation...\n")
    response = add_google_calendar_event.invoke({
        "calendar_id": TARGET_EMAIL,
        "summary": "Agentic AI Architecture Review",
        "description": "Discussing LangGraph orchestration with the team.",
        "hours_from_now": 2
    })
    print(response)

    print("\n--- Testing: Upcoming Events (Coral SQL WHERE Clause) ---")
    print(get_upcoming_events.invoke({"calendar_id": TARGET_EMAIL}))
    
    print("\n--- Testing: Date Range Query (Coral SQL WHERE Clause) ---")
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    print(get_events_by_date_range.invoke({
        "calendar_id": TARGET_EMAIL, 
        "start_date": start, 
        "end_date": end
    }))
    
    print("\n--- Testing: Top 5 Recently Updated (Coral SQL) ---")
    print(get_recently_updated_events.invoke({"calendar_id": TARGET_EMAIL}))

if __name__ == "__main__":
    main()