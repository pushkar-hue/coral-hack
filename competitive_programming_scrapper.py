import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta, timezone

class CompetitiveProgrammingScraper:
    def __init__(self, username):
        self.username = username
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def safe_int(self, value):
        """Helper to safely convert scraped text to integer, preventing empty string crashes."""
        if not value:
            return None
        clean_value = ''.join(filter(str.isdigit, str(value)))
        return int(clean_value) if clean_value else None

    def calculate_stars(self, rating):
        """Manually calculates CodeChef stars based on official rating bands."""
        if rating is None:                                          
            return None
        if rating < 1400:
            return 1
        elif rating < 1600:
            return 2
        elif rating < 1800:
            return 3
        elif rating < 2000:
            return 4
        elif rating < 2200:
            return 5
        elif rating < 2500:
            return 6
        else:
            return 7

    def get_leetcode_data(self):
        """Fetches general stats AND topic-wise stats from LeetCode's GraphQL API."""
        url = "https://leetcode.com/graphql/"
        
        query = f"""
        {{
          matchedUser(username: "{self.username}") {{
            submitStats: submitStatsGlobal {{
              acSubmissionNum {{
                difficulty
                count
              }}
            }}
            tagProblemCounts {{
              advanced {{
                tagName
                problemsSolved
              }}
              intermediate {{
                tagName
                problemsSolved
              }}
              fundamental {{
                tagName
                problemsSolved
              }}
            }}
          }}
        }}
        """
        
        try:
            response = requests.post(url, json={'query': query})
            response.raise_for_status()
            data = response.json().get('data', {}).get('matchedUser', {})
            
            if not data:
                return {"error": "User not found or API changed."}

            # 1. Parse Difficulty Profile Stats
            stats = data.get('submitStats', {}).get('acSubmissionNum', [])
            profile_stats = {
                "username": self.username,
                "easy_solved": 0,
                "medium_solved": 0,
                "hard_solved": 0
            }
            
            for item in stats:
                difficulty = item.get('difficulty')
                count = item.get('count')
                if difficulty == "Easy":
                    profile_stats["easy_solved"] = count
                elif difficulty == "Medium":
                    profile_stats["medium_solved"] = count
                elif difficulty == "Hard":
                    profile_stats["hard_solved"] = count

            # 2. Parse Topic-Wise Stats
            topics_data = data.get('tagProblemCounts', {})
            topics_list = []
            
            for level in ['fundamental', 'intermediate', 'advanced']:
                for tag in topics_data.get(level, []):
                    topics_list.append({
                        "topic_name": tag.get('tagName'),
                        "solved_count": tag.get('problemsSolved')
                    })
                    
            return {
                "profile": profile_stats,
                "topics": topics_list
            }
            
        except Exception as e:
            return {"error": f"Failed to fetch LeetCode data: {str(e)}"}

    def get_codechef_stats(self):
        """Scrapes rating and rank statistics from the CodeChef profile page."""
        url = f"https://www.codechef.com/users/{self.username}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract Rating
            rating_element = soup.find(class_="rating-number")
            current_rating = self.safe_int(rating_element.text if rating_element else None)
            
            # Extract Stars
            star_element = soup.find(class_="rating-star")
            stars = self.safe_int(star_element.text if star_element else None)
            
            # Fallback logic: If DOM parsing fails but we have the rating, calculate manually
            if stars is None and current_rating is not None:
                stars = self.calculate_stars(current_rating)
                
            # Extract Global Rank
            global_rank = None
            rank_list = soup.find(class_="rating-ranks")
            if rank_list:
                rank_link = rank_list.find('a')
                if rank_link:
                    global_rank = self.safe_int(rank_link.text)
                    

            codechef_data = {
                "username": self.username,
                "current_rating": current_rating,
                "global_rank": global_rank,
                "stars": stars
            }
            with open("codechef_profile.jsonl", "a") as f:
                 f.write(json.dumps(codechef_data) + "\n")

            return codechef_data 
            
        except Exception as e:
            return {"error": f"Failed to fetch CodeChef data: {str(e)}"}

def get_upcoming_competitions():
    """Fetches upcoming coding competitions from Codeforces, LeetCode, and CodeChef."""
    competitions = []
    
    # Codeforces API
    try:
        response = requests.get('https://codeforces.com/api/contest.list')
        data = response.json()
        if data.get('status') == 'OK':
            cf_upcoming = [c for c in data['result'] if c.get('phase') == 'BEFORE']
            # Sort by startTimeSeconds
            cf_upcoming.sort(key=lambda x: x.get('startTimeSeconds', float('inf')))
            for c in cf_upcoming[:2]: # Get next 2
                start_dt = datetime.fromtimestamp(c.get('startTimeSeconds'), tz=timezone.utc)
                competitions.append({
                    "platform": "Codeforces",
                    "name": c.get('name'),
                    "start_time_utc": start_dt.isoformat()
                })
    except Exception as e:
        print(f"Failed to fetch Codeforces contests: {e}")

    # LeetCode and CodeChef calculation
    def get_next_weekday(dt, weekday_idx, hour_utc, minute_utc):
        days_ahead = weekday_idx - dt.weekday()
        if days_ahead <= 0:
            if days_ahead == 0 and (dt.hour < hour_utc or (dt.hour == hour_utc and dt.minute < minute_utc)):
                days_ahead = 0
            else:
                days_ahead += 7
        next_date = dt + timedelta(days=days_ahead)
        return next_date.replace(hour=hour_utc, minute=minute_utc, second=0, microsecond=0)

    now_utc = datetime.now(timezone.utc)
    
    # Leetcode: Sunday (6) 02:30 UTC
    next_lc = get_next_weekday(now_utc, 6, 2, 30)
    competitions.append({
        "platform": "LeetCode",
        "name": "Weekly Contest",
        "start_time_utc": next_lc.isoformat()
    })
    
    # Codechef: Wednesday (2) 14:30 UTC
    next_cc = get_next_weekday(now_utc, 2, 14, 30)
    competitions.append({
        "platform": "CodeChef",
        "name": "Weekly Contest",
        "start_time_utc": next_cc.isoformat()
    })

    return competitions

if __name__ == "__main__":
    target_username = "notaceninja"
    scraper = CompetitiveProgrammingScraper(target_username)
    
    print("--- Fetching LeetCode Data ---")
    leetcode_data = scraper.get_leetcode_data()
    print(json.dumps(leetcode_data, indent=2))
    
    print("\n--- Fetching CodeChef Data ---")
    codechef_data = scraper.get_codechef_stats()
    print(json.dumps(codechef_data, indent=2))