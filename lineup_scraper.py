import requests

def get_lineups_for_date(target_date):
    url = f"https://mattgorb.github.io/dailymlblineups/{target_date}.json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
    except Exception as e:
        print(f"❌ Error fetching lineups for {target_date}: {e}")
        return []

    results = []

    for game in data:
        team_abbr = game.get("team")
        players = game.get("lineup", [])
        venue = game.get("venue", "")
        weather = game.get("weather", {})

        if not team_abbr or not players:
            continue

        lineup = []
        for player in players:
            lineup.append({
                "name": player["name"],
                "mlbamId": player.get("mlbamId"),
                "slot": player.get("battingOrder", 0)
            })

        results.append({
            "team": team_abbr,
            "players": sorted(lineup, key=lambda p: p["slot"]),
            "venue": venue,
            "weather": weather
        })

    return results
