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
        if not team_abbr or not players:
            continue

        results.append({
            "team": team_abbr,
            "players": [
                {
                    "name": p["name"],
                    "mlbamId": p["mlbamId"],
                    "slot": p.get("battingOrder", 0)
                }
                for p in players
            ]
        })

    return results
