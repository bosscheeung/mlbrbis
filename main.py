from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import date, timedelta, datetime

from lineup_scraper import get_lineups_for_date
from savant_scraper import get_recent_form_real, get_pitch_type_edge_real

import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Enable CORS for GPT plugin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/openapi.yaml", include_in_schema=False)
def serve_yaml():
    return FileResponse("openapi.yaml", media_type="text/yaml")@app.get("/api/v1/audit/{target}")
def audit_lineups(target: str):
    if target.lower() == "today":
        target_date = date.today().isoformat()
    elif target.lower() == "yesterday":
        target_date = (date.today() - timedelta(days=1)).isoformat()
    else:
        try:
            datetime.strptime(target, "%Y-%m-%d")
            target_date = target
        except ValueError:
            return {"error": "Invalid date format. Use 'today', 'yesterday', or YYYY-MM-DD."}

    lineups = get_lineups_for_date(target_date)
    if not lineups:
        return {"message": f"No lineups available for {target_date}."}

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
        return None
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
    def get_sp_handedness():
        try:
            team_url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
            team_res = requests.get(team_url).json()
            team_id = next(t["id"] for t in team_res["teams"] if t["abbreviation"] == team_abbr)
            roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/active"
            players = requests.get(roster_url).json().get("roster", [])
            for p in players:
                if "P" in p["position"]["abbreviation"]:
                    pid = p["person"]["id"]
                    detail = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}").json()
                    return detail["people"][0]["pitchHand"]["code"]
        except:
            return "R"

    def get_xera_hr9():
        try:
            r = requests.get("https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=0&type=1&season=2025", headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for row in soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 12 and team_abbr.upper() in cols[2].text.strip().upper():
                    return {
                        "xERA": float(cols[11].text.strip()),
                        "hrPer9": float(cols[8].text.strip())
                    }
        except:
            pass
        return {"xERA": 4.25, "hrPer9": 1.3}

    def get_bullpen_fatigue():
        try:
            r = requests.get("https://www.rotowire.com/baseball/bullpen-report.php", headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.content, "html.parser")
            for block in soup.select(".lineup"):
                abbr = block.select_one(".lineup__abbr")
                if abbr and abbr.text.strip().upper() == team_abbr.upper():
                    count = sum("20" in p.text for p in block.select(".lineup__player__stats"))
                    return 2.5 if count >= 3 else 1.0
        except:
            pass
        return 1.0

    return {
        "handedness": get_sp_handedness(),
        **get_xera_hr9(),
        "bullpenFatigueScore": get_bullpen_fatigue()
    }
def get_run_environment(team_abbr):
    def get_park_factor():
        try:
            r = requests.get("https://www.espn.com/mlb/stats/parkfactor", headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for row in soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3 and team_abbr.upper() in cols[0].text.strip().upper():
                    return float(cols[2].text.strip())
        except:
            pass
        return 100.0

    def get_vegas_totals():
        try:
            r = requests.get("https://www.vegasinsider.com/mlb/odds/las-vegas/", headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.content, "html.parser")
            for game in soup.select(".viGameScorebox"):
                teams = game.select(".viTeamName")
                odds = game.select(".viConsensusLine")
                if len(teams) >= 2 and odds:
                    t1, t2 = teams[0].text.strip().upper(), teams[1].text.strip().upper()
                    total = float(odds[0].text.strip().split()[0])
                    if team_abbr.upper() == t1:
                        return {"vegasTotal": total, "teamTotal": round(total * 0.55, 2)}
                    if team_abbr.upper() == t2:
                        return {"vegasTotal": total, "teamTotal": round(total * 0.45, 2)}
        except:
            pass
        return {"vegasTotal": 9.0, "teamTotal": 4.5}

    return {
        "parkFactor": get_park_factor(),
        "weather": {
            "temperature": 75,  # stub for now
            "windSpeed": 8,
            "windDirection": "Out to LF"
        },
        **get_vegas_totals()
    }
