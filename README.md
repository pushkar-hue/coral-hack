# The Grandmaster's Ledger

The Grandmaster's Ledger is an autonomous AI training officer designed to optimize your competitive programming and technical interview prep. It takes over the logistics of scheduling, tracking, and resource gathering so you can focus entirely on writing code.

**Hackathon Track:** Track 2 – Personal Agent (Study Planner & Work Prioritizer)

## The Problem It Solves

Training for technical interviews or competitive programming can easily turn into a chaotic mess. You're constantly jumping between platforms, trying to figure out which topics you're weak at, hunting down YouTube tutorials, and trying to remember when the next Codeforces contest is happening. Managing this scattered schedule takes almost as much mental energy as solving the problems themselves. I built this project to completely eliminate that cognitive load.

## What I Built

I created a terminal-based autonomous agent (powered by LangChain and OpenRouter) that acts as your personal coding coach. Instead of just giving you generic advice, the agent actively orchestrates your study plan. It analyzes your performance, identifies your algorithmic weak points, and schedules dedicated focus blocks directly into your calendar. On top of that, it searches the web for the exact LeetCode problems or video tutorials you need and pushes them straight into your Notion workspace.

## How I Used Coral (The Data Engine)

Initially, the agent relied on messy, fragmented Python scraping scripts and isolated API calls. To align with the ultimate vision of a unified data layer, I completely re-architected the system to run on **Coral SQL**.

I authored **Custom Source Specs (manifest.yaml)** to turn live web platforms into virtual, queryable databases:

* **LeetCode (`leetcode.yaml`):** Built an HTTP-backed source that dynamically templates GraphQL POST requests to extract topic-wise solved counts.
* **Codeforces (`codeforces.yaml`):** Mapped their public REST API to pull live global ratings and ranks.
* **CodeChef (`codechef.yaml`):** Created a Local JSONL Bridge to ingest scraped profile metrics natively into Coral.
* **Google Calendar (`google_calendar.yaml`):** Utilized Coral's built-in OAuth authorization-code flow to securely fetch upcoming schedule availability.

### The "Meaningful JOIN"

Because all platforms are now unified under Coral, the agent's "brain" operates on a single, powerful cross-platform SQL query. Instead of making three different API calls, the agent executes this exact JOIN to instantly find out what topics you are failing at, and cross-references your Google Calendar to see if you've actually carved out time to study them:

```sql
SELECT 
    l."tagName" AS weak_topic, 
    l."problemsSolved", 
    c.summary AS scheduled_focus_block
FROM 
    leetcode.topic_stats l
LEFT JOIN 
    google_calendar.events c 
    ON c.summary ILIKE '%' || l."tagName" || '%'
WHERE 
    l."problemsSolved" < 15
ORDER BY 
    l."problemsSolved" ASC
LIMIT 5;
```

### Hybrid Architecture

Coral handles the declarative **Reads** (federated SQL joins to find weak spots), while the Python LangChain agent handles the active **Writes** (using APIs to actually insert events into Google Calendar and push tasks to Notion).

## Demo & Setup

If you want to spin up your own training officer, getting the project running locally requires setting up both the Coral Data Layer and the Python Agent.

### 1. Environment Setup

Clone the repository and create a `.env` file in the root directory:

```bash
git clone https://github.com/yourusername/coral-hack.git
cd coral-hack
```

```bash
# Example .env structure
LEETCODE_USERNAME=your_username
CODECHEF_USERNAME=your_username
GOOGLE_CALENDAR_ID=your_email
OPENROUTER_API_KEY=your_key
SERPER_API_KEY=your_key
NOTION_API_KEY=your_key
```

### 2. Initialize the Coral Data Layer

You need to add the custom source specs to your local Coral workspace. The calendar integration will automatically open your browser for OAuth authentication.

```bash
coral source add --file ./leetcode.yaml --interactive
coral source add --file ./codeforces.yaml --interactive
coral source add --file ./google_calendar.yaml --interactive
```

For CodeChef (which uses the local JSONL bridge), generate the initial data file first, then add the source:

```bash
python competitive_programming_scrapper.py
coral source add --file ./codechef.yaml
```

### 3. Boot the Agent

Once your environment is ready, your dependencies are installed, and Coral is federated, spin up the terminal UI:

```bash
python agent.py
```

*(Note: The terminal supports multi-line pasting. Press Enter on an empty line to send your prompt to the agent!)*

## What's Next

Right now, the agent is fantastic at curating resources and managing your time based on topic-level weaknesses across LeetCode, CodeChef, and Codeforces. Looking ahead, I plan to expand its capabilities to include deeper, code-level analytics so it can pinpoint specific algorithmic misunderstandings based on your actual source code submissions. I'm also looking to build out a more streamlined graphical onboarding experience so anyone can set up their own personalized grandmaster without touching a `.yaml` file.
