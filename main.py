from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import date
import requests
import re
from bs4 import BeautifulSoup

from lineup_scraper import get_today_lineups
from id_mapper import load_chadwick_mapping, normalize_name
from savant_scraper import get_recent_form_real, get_pitch_type_edge_real

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/openapi.yaml", include_in_schema=False)
def serve_yaml():
    return FileResponse("openapi.yaml", media_type="text/yaml")

@app.get("/api/v1/audit/today")
def audit_today():
    lineups = get_today_lineups()
    chadwick = load_chadwick_mapping()
    results = []

    for team_lineup in lineups:
        team = team_lineup["team"]
        confirmed = team_lineup.get("confirmed", False)
        weather = get_weather_scrape(team)

        for player in team_lineup["players"]:
            name = player["name"]
            key = normalize_name(name)
            mlbam_id = chadwick.get(key)

            power = get_power_metrics(mlbam_id) if mlbam_id else None
            recent = get_recent_form_real(mlbam_id) if mlbam_id else {}
            pitch = get_pitch_type_edge_real(mlbam_id) if mlbam_id else {}

            results.append({
                "name": name,
                "team": team,
                "mlbamId": mlbam_id,
                "slot": player["slot"],
                "confirmed": confirmed,
                "audit": {
                    "powerSignal": power or {"note": "Missing MLBAM ID"},
                    "volumeOpportunity": {
                        "slot": player["slot"],
                        "projectedPAs": get_projected_pa(name)
                    },
                    "opponentWeakness": get_opponent_stats(team),
                    "runEnvironment": get_run_environment(team, weather),
                    "recentForm": recent,
                    "pitchEdge": pitch
                }
            })

    return results
def get_power_metrics(mlbam_id):
    try:
        url = "https://baseballsavant.mlb.com/leaderboard/statcast?type=batter&stat=barrel_rate&year=2025&min=1&sort=7&csv=false"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("data", [])
        for row in data:
            if str(row.get("player_id")) == str(mlbam_id):
                return {
                    "barrelRate": float(row.get("brl_percent", 0)),
                    "xSLG": float(row.get("estimated_slg", 0)),
                    "hardHitPercent": float(row.get("hard_hit_percent", 0)),
                    "avgExitVelocity": float(row.get("avg_hit_speed", 0))
                }
    except:
        pass
    return None
def get_projected_pa(name):
    try:
        r = requests.get("https://www.fangraphs.com/projections?pos=all&stats=bat&type=fangraphsdc", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 6:
                player = cols[0].text.strip().lower().replace(".", "").replace(" jr", "")
                if name.lower().replace(".", "").replace(" jr", "") in player:
                    return int(cols[5].text.strip())
    except:
        pass
    return 5
def get_opponent_stats(team_abbr):
    return {
        "handedness": "R",
        "xERA": 4.25,
        "hrPer9": 1.3,
        "bullpenFatigueScore": 2.0
    }
PARK_FACTORS_2025 = {
    "Progressive Field": 98,
    "Coors Field": 117,
    "Yankee Stadium": 102,
    "Dodger Stadium": 101,
    "Fenway Park": 105,
    "Great American Ball Park": 113
    # Add more as needed
}
def get_run_environment(team_abbr, weather_data=None):
    return {
        "parkFactor": PARK_FACTORS_2025.get(team_abbr.upper(), 100),
        "weather": weather_data or {
            "temperature": 75,
            "windSpeed": 8,
            "windDirection": "Unknown"
        },
        "vegasTotal": 9.0,
        "teamTotal": 4.5
    }
def get_weather_scrape(team_abbr):
    try:
        url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=today"
        schedule = requests.get(url).json()

        for game in schedule.get("dates", [])[0].get("games", []):
            teams = game.get("teams", {})
            for side in ["home", "away"]:
                info = teams.get(side, {}).get("team", {})
                if info.get("abbreviation", "").upper() == team_abbr.upper():
                    preview_url = f"https://www.mlb.com{game.get('content', {}).get('link', '')}"
                    page = requests.get(preview_url).text
                    soup = BeautifulSoup(page, "html.parser")
                    weather_text = soup.get_text()
                    return parse_weather_string(weather_text)
    except Exception as e:
        print(f"❌ Weather scrape error: {e}")

    return {
        "temperature": 75,
        "windSpeed": 8,
        "windDirection": "Unknown"
    }

def parse_weather_string(text):
    temp_match = re.search(r"(\d{2,3}) ?°F", text)
    wind_match = re.search(r"Wind:? (\d{1,2}) mph (Out|In|Left|Right|Center|to [A-Z]+)", text, re.IGNORECASE)

    return {
        "temperature": int(temp_match.group(1)) if temp_match else 75,
        "windSpeed": int(wind_match.group(1)) if wind_match else 8,
        "windDirection": wind_match.group(2) if wind_match else "Unknown"
    }
