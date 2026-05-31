# The Grandmaster's Ledger

The Grandmaster's Ledger is an autonomous AI training officer designed to optimize your competitive programming and technical interview prep. It takes over the logistics of scheduling, tracking, and resource gathering so you can focus entirely on writing code.

<!-- PLACEHOLDER: Add a screenshot of the agent in action here -->
![The Agent in Action](placeholder_screenshot_1.png)

## The Problem It Solves

Training for technical interviews or competitive programming can easily turn into a chaotic mess. You're constantly jumping between platforms, trying to figure out which topics you're weak at, hunting down YouTube tutorials, and trying to remember when the next Codeforces contest is happening. Managing this scattered schedule takes almost as much mental energy as solving the problems themselves. I built this project to completely eliminate that cognitive load.

## What I Built

I created an autonomous agent that acts as your personal coding coach. Instead of just giving you generic advice, the agent actively orchestrates your study plan. It analyzes your performance, identifies your weak points, and schedules dedicated focus blocks directly into your calendar. On top of that, it searches the web for the exact LeetCode problems or video tutorials you need and pushes them straight into your workspace.

## How I Used Coral (And Connected Data Sources)

At its core, the agent needs context to make smart decisions. I used Coral to build a unified data layer that seamlessly connects all the moving parts of the system. 

Through Coral, the agent pulls real-time statistics from **LeetCode** and **CodeChef** to track your progress. It fetches upcoming coding competitions and directly schedules them into your **Google Calendar**. For curriculum organization, it integrates deeply with **Notion**. The agent doesn't just write text; it actively creates study tasks and embeds sleek, clickable bookmarks and video resources into your Notion notes. 

Coral acts as the bridge here. Rather than writing messy, fragmented API calls for every single platform, Coral allows the agent to query your competitive ranking, your daily agenda, and your study notes in one unified flow.

<!-- PLACEHOLDER: Add a screenshot of the Notion integration and Calendar scheduling here -->
![Notion and Calendar Integration](placeholder_screenshot_2.png)

## Demo & Setup

If you want to spin up your own training officer, getting the project running locally is straightforward. 

First, clone the repository and navigate into the project folder:

```bash
git clone https://github.com/yourusername/coral-hack.git
cd coral-hack
```

You'll need to set up your environment variables. Create a `.env` file in the root directory and add your specific Notion database IDs, Google Calendar credentials, and API keys (like OpenRouter and Serper):

```bash
# Example .env structure
LEETCODE_USERNAME=your_username
CODECHEF_USERNAME=your_username
GOOGLE_CALENDAR_ID=your_email
OPENROUTER_API_KEY=your_key
SERPER_API_KEY=your_key
```

Once your environment is ready and the Python dependencies are installed, you simply run the agent script:

```bash
python agent.py
```

## What's Next

Right now, the agent is fantastic at curating resources and managing your time based on topic-level weaknesses. Looking ahead, I plan to expand its capabilities to include deeper, code-level analytics so it can pinpoint specific algorithmic misunderstandings based on your actual submissions. I'm also looking to integrate additional platforms like Codeforces and build out a more streamlined onboarding experience so anyone can set up their own personalized grandmaster in minutes.
