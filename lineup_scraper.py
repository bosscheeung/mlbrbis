import requests

def get_lineups_for_date(target_date: str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date}&hydrate=lineups,probablePitcher"
    r = requests.get(url, timeout=10)
    data = r.json()

    results = []

    for game in data.get("dates", [])[0].get("games", []):
        for team_side in ["away", "home"]:
            team_data = game.get("teams", {}).get(team_side, {})
            team_info = team_data.get("team", {})
            team_abbr = team_info.get("abbreviation") or team_info.get("name")
            lineup = team_data.get("lineup", {}).get("lineupPositions", [])

            if not team_abbr or not lineup:
                continue

            players = []
            for spot in lineup:
                player = spot.get("player")
                if player:
                    players.append({
                        "name": player["fullName"],
                        "mlbamId": player["id"],
                        "slot": spot["battingOrder"]
                    })

            results.append({
                "team": team_abbr,
                "players": sorted(players, key=lambda p: int(p["slot"]))
            })

    return results
