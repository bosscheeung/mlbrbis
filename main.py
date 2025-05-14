from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from lineup_scraper import get_today_lineups
from savant_scraper import get_recent_form_real, get_pitch_type_edge_real

import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Enable GPT plugin access
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

@app.get("/api/v1/debug/lineups")
def debug_lineups():
    return get_today_lineups()
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
    except Exception:
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
    except Exception:
        pass
    return 5
def get_opponent_stats(team_abbr):
    return {
        "handedness": "R",
        "xERA": 4.25,
        "hrPer9": 1.3,
        "bullpenFatigueScore": 2.0
    }

def get_run_environment(team_abbr):
    return {
        "parkFactor": 101,
        "weather": {
            "temperature": 75,
            "windSpeed": 9,
            "windDirection": "Out to LF"
        },
        "vegasTotal": 9.0,
        "teamTotal": 4.5
    }
@app.get("/api/v1/audit/today")
def audit_all_today_hitters():
    lineups = get_today_lineups()
    results = []

    for team_lineup in lineups:
        team = team_lineup["team"]
        for player in team_lineup["players"]:
            name = player["name"]
            mlbam_id = player["mlbamId"]

            power = get_power_metrics(mlbam_id)
            recent = get_recent_form_real(mlbam_id)
            pitch = get_pitch_type_edge_real(mlbam_id)

            results.append({
                "name": name,
                "team": team,
                "mlbamId": mlbam_id,
                "slot": player["slot"],
                "audit": {
                    "powerSignal": power or {"note": "Power data not available"},
                    "volumeOpportunity": {
                        "slot": player["slot"],
                        "projectedPAs": get_projected_pa(name)
                    },
                    "opponentWeakness": get_opponent_stats(team),
                    "runEnvironment": get_run_environment(team),
                    "recentForm": recent,
                    "pitchEdge": pitch
                }
            })

    return results
