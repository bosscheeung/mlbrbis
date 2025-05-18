from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import re
import requests
from bs4 import BeautifulSoup

from id_mapper import load_chadwick_mapping, normalize_name
from weather_scraper import get_weather_scrape
from savant_scraper import get_recent_form_real, get_pitch_type_edge_real

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "MLB audit API running"}

@app.get("/openapi.yaml", include_in_schema=False)
def serve_yaml():
    return FileResponse("openapi.yaml", media_type="text/yaml")

@app.post("/api/v1/audit/parse")
async def audit_from_text(request: Request):
    body = await request.json()
    text = body.get("text", "")
    if not text.strip():
        return {"error": "Missing lineup text"}

    chadwick = load_chadwick_mapping()
    games = parse_full_lineup_block(text)
    results = []

    for game in games:
        team = game["team"]
        players = game["players"]
        weather = get_weather_scrape(team)

        for player in players:
            name = player["name"]
            slot = player["slot"]
            key = normalize_name(name)
            mlbam_id = chadwick.get(key)

            power = get_power_metrics(mlbam_id) if mlbam_id else None
            recent = await get_recent_form_real(mlbam_id) if mlbam_id else {}
            pitch = await get_pitch_type_edge_real(mlbam_id) if mlbam_id else {}

            results.append({
                "name": name,
                "team": team,
                "mlbamId": mlbam_id,
                "slot": slot,
                "confirmed": False,
                "audit": {
                    "powerSignal": power or {"note": "Missing MLBAM ID"},
                    "volumeOpportunity": {
                        "slot": slot,
                        "projectedPAs": get_projected_pa(name)
                    },
                    "opponentWeakness": get_opponent_stats(team),
                    "runEnvironment": get_run_environment(team, weather),
                    "recentForm": recent,
                    "pitchEdge": pitch
                }
            })

    return results

def parse_full_lineup_block(text):
    lines = text.splitlines()
    team_blocks = []
    current_team = ""
    players = []
    reading_players = False
    slot = 0

    for line in lines:
        clean = line.strip()
        if "Lineup" in clean and not clean.startswith("#"):
            if current_team and players:
                team_blocks.append({"team": current_team, "players": players})
            current_team = clean.replace("Lineup", "").strip()
            players = []
            slot = 0
            reading_players = True
            continue

        if reading_players:
            match = re.match(r"(\d+)[.)]?\s+([A-Za-z .'-]+)", clean)
            if match:
                slot += 1
                player_name = match.group(2).strip()
                players.append({"name": player_name, "slot": slot})
            elif clean.lower().startswith("weather") or clean.lower().startswith("gametime"):
                reading_players = False

    if current_team and players:
        team_blocks.append({"team": current_team, "players": players})

    return team_blocks

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
