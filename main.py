from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

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
            # ✅ Only include games that haven’t started yet
            if game.get("status", {}).get("abstractGameState") != "Preview":
                continue

            gamePk = game["gamePk"]
            game_info = {
                "game": f"{game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}",
                "homeTeam": game['teams']['home']['team']['name'],
                "awayTeam": game['teams']['away']['team']['name'],
                "homeLineup": [],
                "awayLineup": []
            }

            # Get boxscore
            boxscore_url = f"https://statsapi.mlb.com/api/v1/game/{gamePk}/boxscore"
            boxscore_response = requests.get(boxscore_url)
            if boxscore_response.status_code != 200:
                continue

            boxscore_data = boxscore_response.json()
            teams = boxscore_data.get("teams", {})
            total_confirmed = 0

            for side in ["home", "away"]:
                lineup = []
                players = teams.get(side, {}).get("players", {})
                for player in players.values():
                    if "battingOrder" in player:
                        lineup.append({
                            "fullName": player.get("person", {}).get("fullName", ""),
                            "position": player.get("position", {}).get("abbreviation", ""),
                            "battingOrder": player.get("battingOrder", "")
                        })

                game_info[f"{side}Lineup"] = lineup
                total_confirmed += len(lineup)

            # ✅ Only include if lineups are confirmed (i.e. players have battingOrder)
            if total_confirmed > 0:
                result.append(game_info)

    return result
