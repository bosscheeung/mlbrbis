import requests
from bs4 import BeautifulSoup

def get_today_lineups():
    url = "https://www.fantasypros.com/mlb/lineups/today/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, "html.parser")

    results = []
    lineup_sections = soup.select(".lineup__card")

    for card in lineup_sections:
        try:
            team_name = card.select_one(".lineup__team__abbr").text.strip()
            players = []
            rows = card.select(".lineup__player")
            for i, row in enumerate(rows):
                name = row.select_one(".lineup__player__name").text.strip()
                players.append({"name": name, "slot": i + 1})
            results.append({"team": team_name, "players": players})
        except Exception as e:
            print(f"❌ Lineup parsing error: {e}")
    
    return results
