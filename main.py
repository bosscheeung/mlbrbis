from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Allow GPT/plugin access
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
        "hydrate": "team.lineups"
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
                team_data = game['teams'][side]
                players = team_data.get("lineups", {}).get("lineup", [])
                parsed_players = []

                for player in players:
                    parsed_players.append({
                        "fullName": player.get("fullName"),
                        "position": player.get("position", {}).get("abbreviation", ""),
                        "battingOrder": player.get("battingOrder", "")
                    })

                game_obj[f"{side}Lineup"] = parsed_players

            result.append(game_obj)

    return result
