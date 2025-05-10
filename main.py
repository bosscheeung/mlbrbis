from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Allow GPT/plugin calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/lineups")
def get_lineups(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
    schedule_params = {
        "sportId": 1,
        "date": date
    }

    schedule_response = requests.get(schedule_url, params=schedule_params)
    schedule_data = schedule_response.json()
    result = []

    for game_date in schedule_data.get("dates", []):
        for game in game_date.get("games", []):
            gamePk = game["gamePk"]
            game_info = {
                "game": f"{game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}",
                "homeTeam": game['teams']['home']['team']['name'],
                "awayTeam": game['teams']['away']['team']['name'],
                "homeLineup": [],
                "awayLineup": []
            }

            # Fetch boxscore for lineups
            boxscore_url = f"https://statsapi.mlb.com/api/v1/game/{gamePk}/boxscore"
            boxscore_response = requests.get(boxscore_url)
            boxscore_data = boxscore_response.json()

            players = boxscore_data.get("teams", {})
            for side in ["home", "away"]:
                team = players.get(side, {})
                for player in team.get("players", {}).values():
                    stats = player.get("stats", {})
                    if "battingOrder" in player:
                        game_info[f"{side}Lineup"].append({
                            "fullName": player.get("person", {}).get("fullName", ""),
                            "position": player.get("position", {}).get("abbreviation", ""),
                            "battingOrder": player.get("battingOrder", "")
                        })

            result.append(game_info)

    return result
