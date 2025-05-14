import requests
from bs4 import BeautifulSoup

def get_today_lineups():
    url = "https://www.fantasypros.com/mlb/lineups/today/"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")

    results = []

    lineup_sections = soup.select(".lineup__card")
    for card in lineup_sections:
        team_name = card.select_one(".lineup__team__abbr").text.strip()
        players = []
        rows = card.select(".lineup__player")
        for i, row in enumerate(rows):
            name = row.select_one(".lineup__player__name").text.strip()
            players.append({"name": name, "slot": i + 1})
        results.append({"team": team_name, "players": players})
    
    return results
