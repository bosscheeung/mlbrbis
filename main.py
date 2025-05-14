from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from id_mapper import load_chadwick_mapping
from lineup_scraper import get_today_lineups
from savant_scraper import get_pitch_type_edge_real, get_recent_form_real

import requests
from bs4 import BeautifulSoup

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

@app.get("/api/v1/debug/ids")
def debug_id(name: str = "ronald acuna jr"):
    chadwick_map = load_chadwick_mapping()
    return {"name": name, "mlbamId": chadwick_map.get(name.lower().strip())}
def get_power_metrics(mlbam_id):
    try:
        url = "https://baseballsavant.mlb.com/leaderboard/statcast?type=batter&stat=barrel_rate&year=2025&min=1&sort=7&csv=false"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        for row in data["data"]:
            if str(row.get("player_id")) == str(mlbam_id):
                return {
                    "barrelRate": float(row.get("brl_percent", 0)),
                    "xSLG": float(row.get("estimated_slg", 0)),
                    "hardHitPercent": float(row.get("hard_hit_percent", 0)),
                    "avgExitVelocity": float(row.get("avg_hit_speed", 0))
                }
    except:
        return None
    return None

def get_projected_pa(name):
    try:
        r = requests.get("https://www.fangraphs.com/projections?pos=all&stats=bat&type=fangraphsdc", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 6:
                player = cols[0].text.strip().lower().replace(".", "").replace(" jr", "")
                if name.lower().replace(".", "").replace(" jr", "") in player:
                    return int(cols[5].text.strip())
    except:
        return 5
    return 5

def get_opponent_stats(team_abbr):
    try:
        return {
            "handedness": "R",  # replace with MLB API if needed
            "xERA": 4.25,
            "hrPer9": 1.3,
            "bullpenFatigueScore": 2.0
        }
    except:
        return {}

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
    chadwick_map = load_chadwick_mapping()
    lineups = get_today_lineups()
    results = []

    for team_lineup in lineups:
        team = team_lineup["team"]
        for player in team_lineup["players"]:
            name = player["name"]
            name_key = name.lower().strip()
            mlbam_id = chadwick_map.get(name_key)
            if not mlbam_id:
                continue

            try:
                power = get_power_metrics(mlbam_id)
                if not power:
                    continue

                opponent = get_opponent_stats(team)
                run_env = get_run_environment(team)
                recent = get_recent_form_real(mlbam_id)
                pitch = get_pitch_type_edge_real(mlbam_id)
                pa = get_projected_pa(name)

                results.append({
                    "name": name,
                    "team": team,
                    "mlbamId": mlbam_id,
                    "slot": player["slot"],
                    "audit": {
                        "powerSignal": power,
                        "volumeOpportunity": {
                            "slot": player["slot"],
                            "projectedPAs": pa
                        },
                        "opponentWeakness": opponent,
                        "runEnvironment": run_env,
                        "recentForm": recent,
                        "pitchEdge": pitch
                    }
                })
            except Exception as e:
                print(f"❌ Error processing {name}: {e}")
                continue

    return results
