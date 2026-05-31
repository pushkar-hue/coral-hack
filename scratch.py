import requests
import json

try:
    response = requests.get('https://codeforces.com/api/contest.list')
    data = response.json()
    if data['status'] == 'OK':
        upcoming = [c for c in data['result'] if c['phase'] == 'BEFORE']
        print(f"Found {len(upcoming)} upcoming Codeforces contests.")
        for c in upcoming[:2]:
            print(c['name'])
except Exception as e:
    print(e)
