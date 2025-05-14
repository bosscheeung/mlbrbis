from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from id_mapper import load_chadwick_mapping, normalize_name
from lineup_scraper import get_today_lineups
from savant_scraper import get_recent_form_real, get_pitch_type_edge_real

import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Enable CORS so GPT can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve your OpenAPI spec
@app.get("/openapi.yaml", include_in_schema=False)
def serve_yaml():
    return FileResponse("openapi.yaml", media_type="text/yaml")

# Debug Chadwick ID mapping
@app.get("/api/v1/debug/ids")
def debug_id(name: str = "ronald acuna jr"):
    chadwick_map = load_chadwick_mapping()
    key = normalize_name(name)
    return {"name": name, "mlbamId": chadwick_map.get(key)}
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
        r = requests.get(
            "https://www.fangraphs.com/projections?pos=all&stats=bat&type=fangraphsdc",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10
        )
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 6:
                player = cols[0].text.strip().lower().replace(".", "").replace(" jr", "")
                if normalize_name(name) in player:
                    return int(cols[5].text.strip())
    except Exception:
        pass
    return 5

def get_fangraphs_sp_stats(team_abbr):
    try:
        r = requests.get(
            "https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=10&type=1&season=2025",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10
        )
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"class": "rgMasterTable"})
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if cols[2].text.strip().upper() == team_abbr.upper():
                return {
                    "xERA": float(cols[11].text.strip()),
                    "hrPer9": float(cols[8].text.strip())
                }
    except Exception:
        pass
    return {"xERA": None, "hrPer9": None}

def get_bullpen_fatigue_score(team_abbr):
    try:
        r = requests.get("https://www.rotowire.com/baseball/bullpen-report.php",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        for block in soup.select(".lineup"):
            abbr = block.select_one(".lineup__abbr")
            if abbr and abbr.text.strip().upper() == team_abbr.upper():
                count = sum("20" in p.text for p in block.select(".lineup__player__stats"))
                return 2.5 if count >= 3 else 1.0
    except Exception:
        pass
    return 1.0

def get_team_drs(team_abbr):
    try:
        r = requests.get(
            "https://www.fangraphs.com/leaders.aspx?pos=all&stats=fld&lg=all&qual=0&type=8&season=2025",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10
        )
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr")[1:]:
            cols = row.find_all("td")
            if team_abbr.upper() in cols[1].text.strip().upper():
                return float(cols[6].text.strip())
    except Exception:
        pass
    return 0.0

def get_sp_handedness(team_abbr):
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?season=2025").json()["teams"]
        team_id = next(t["id"] for t in teams if t["abbreviation"] == team_abbr)
        roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/active").json()["roster"]
        for p in roster:
            if p["position"]["abbreviation"] == "SP":
                pid = p["person"]["id"]
                detail = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}").json()
                return detail["people"][0]["pitchHand"]["code"]
    except Exception:
        pass
    return "R"

def get_park_factor(team_abbr):
    try:
        r = requests.get("https://www.espn.com/mlb/stats/parkfactor", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr")[1:]:
            cols = row.find_all("td")
            if team_abbr.upper() in cols[0].text.strip().upper():
                return float(cols[2].text.strip())
    except Exception:
        pass
    return 100.0

def get_vegas_totals(team_abbr):
    try:
        r = requests.get("https://www.vegasinsider.com/mlb/odds/las-vegas/",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
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
    except Exception:
        pass
    return {"vegasTotal": 9.0, "teamTotal": 4.5}
@app.get("/api/v1/audit/today")
def audit_all_today_hitters():
    chadwick_map = load_chadwick_mapping()
    lineups = get_today_lineups()
    results = []

    for tl in lineups:
        team = tl["team"]
        for player in tl["players"]:
            name = player["name"]
            key = normalize_name(name)
            mlbam_id = chadwick_map.get(key)  # may be None

            power = get_power_metrics(mlbam_id) if mlbam_id else None
            opponent = get_fangraphs_sp_stats(team)
            opponent["handedness"] = get_sp_handedness(team)
            opponent["bullpenFatigueScore"] = get_bullpen_fatigue_score(team)
            opponent["teamDRS"] = get_team_drs(team)

            run_env = get_park_factor(team)  # you can expand to use get_run_environment
            run_env = {
                "parkFactor": run_env,
                "weather": {"temperature": 75, "windSpeed": 9, "windDirection": "Out to LF"},
                **get_vegas_totals(team)
            }

            recent = get_recent_form_real(mlbam_id) if mlbam_id else {"note": "no ID"}
            pitch = get_pitch_type_edge_real(mlbam_id) if mlbam_id else {"note": "no ID"}
            pa = get_projected_pa(name)

            results.append({
                "name": name,
                "team": team,
                "mlbamId": mlbam_id,
                "slot": player["slot"],
                "audit": {
                    "powerSignal": power or {"note": "no ID"},
                    "volumeOpportunity": {"slot": player["slot"], "projectedPAs": pa},
                    "opponentWeakness": opponent,
                    "runEnvironment": run_env,
                    "recentForm": recent,
                    "pitchEdge": pitch
                }
            })

    return results
