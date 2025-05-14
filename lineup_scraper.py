import requests
from bs4 import BeautifulSoup

def get_today_lineups():
    url = "https://www.rotowire.com/baseball/daily-lineups.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, "html.parser")

    results = []

    for card in soup.select(".lineup-card"):
        team_abbr = card.select_one(".lineup__abbr")
        if not team_abbr:
            continue
        team = team_abbr.text.strip()

        players = []
        for i, row in enumerate(card.select(".lineup__player")):
            name_tag = row.select_one(".lineup__player__name")
            if name_tag:
                name = name_tag.text.strip()
                players.append({
                    "name": name,
                    "slot": i + 1
                })

        if players:
            results.append({
                "team": team,
                "players": players
            })

    return results
