from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from datetime import datetime

app = FastAPI()

# Allow GPT/plugin calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/lineups")
def get_lineups(date: str = Query(None, description="Date in YYYY-MM-DD format. Defaults to today.")):
    # Use today’s date if none is provided
    if not date:
        date = datetime.utcnow().strftime('%Y-%m-%d')

    # Step 1: Get schedule for the date
    schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
    schedule_params = {
        "sportId": 1,
        "date": date
    }

    schedule_response = requests.get(schedule_url, params=schedule_params)
    if schedule_response.status_code != 200:
        return JSONResponse(status_code=502, content={"error": "Failed to fetch MLB schedule"})

    schedule_data = schedule_response.json()
    result = []

    for game_date in schedule_data.get("dates", []):
        for game in game_date.get("games", []):
            gamePk = game["gamePk"]

            # Step 2: Fetch boxscore for each game
            boxscore_url = f"https://statsapi.mlb.com/api/v1/game/{gamePk}/boxscore"
            boxscore_response = requests.get(boxscore_url)
            if boxscore_response.status_code != 200:
                continue

            boxscore_data = boxscore_response.json()
            teams = boxscore_data.get("teams", {})
            total_confirmed = 0

            game_info = {
                "game": f"{game['teams']['away']['team']['name']} @ {game['teams']['home']['team']['name']}",
                "homeTeam": game['teams']['home']['team']['name'],
                "awayTeam": game['teams']['away']['team']['name'],
                "homeLineup": [],
                "awayLineup": []
            }

            for side in ["home", "away"]:
                players = teams.get(side, {}).get("players", {})
                lineup = []
                for player in players.values():
                    if "battingOrder" in player:
                        lineup.append({
                            "fullName": player.get("person", {}).get("fullName", ""),
                            "position": player.get("position", {}).get("abbreviation", ""),
                            "battingOrder": player.get("battingOrder", "")
                        })

                # Sort by batting order
                lineup = sorted(
                    lineup,
                    key=lambda x: int(x["battingOrder"]) if x["battingOrder"].isdigit() else 99
                )

                game_info[f"{side}Lineup"] = lineup
                total_confirmed += len(lineup)

            # Only include games with at least one confirmed lineup
            if total_confirmed > 0:
                result.append(game_info)

    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
