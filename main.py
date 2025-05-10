from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Allow GPT plugin calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/lineups")
def get_lineups(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "date": date,
        "hydrate": "lineups"
    }

    response = requests.get(url, params=params)
    data = response.json()
    result = []

    for game_date in data.get("dates", []):
        for game in game_date.get("games", []):
            game_obj = {
                "game": f"{game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}",
                "homeTeam": game['teams']['home']['team']['name'],
                "awayTeam": game['teams']['away']['team']['name'],
                "homeLineup": [],
                "awayLineup": []
            }

            for side in ["home", "away"]:
                team_data = game["teams"].get(side, {})
                lineup_data = team_data.get("lineup", [])

                for player in lineup_data:
                    game_obj[f"{side}Lineup"].append({
                        "fullName": player.get("fullName"),
                        "position": player.get("position", {}).get("abbreviation", ""),
                        "battingOrder": player.get("battingOrder", "")
                    })

            result.append(game_obj)

    return result
