from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from id_mapper import load_chadwick_mapping
from lineup_scraper import get_today_lineups
from savant_scraper import get_pitch_type_edge_real, get_recent_form_real
import requests
from bs4 import BeautifulSoup
from io import StringIO

app = FastAPI()

# CORS for GPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Power Metrics
def get_power_metrics_real(mlbam_id):
    url = "https://baseballsavant.mlb.com/leaderboard/statcast?type=batter&stat=barrel_rate&year=2025&min=1&sort=7&csv=false"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        for row in data["data"]:
            if str(row.get("player_id")) == str(mlbam_id):
                return {
                    "barrelRate": float(row.get("brl_percent", 0)),
                    "xSLG": float(row.get("estimated_slg", 0)),
                    "hardHitPercent": float(row.get("hard_hit_percent", 0)),
                    "avgExitVelocity": float(row.get("avg_hit_speed", 0))
                }
        return None
    except Exception as e:
        print(f"❌ Power metrics error: {e}")
        return None

# ✅ SP Stats from Fangraphs
def get_fangraphs_sp_stats(team_name):
    url = "https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=10&type=1&season=2025"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", {"class": "rgMasterTable"})
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 12:
                continue
            if cols[2].text.strip().upper() == team_name.upper():
                return {
                    "xERA": float(cols[11].text.strip()),
                    "hrPer9": float(cols[8].text.strip())
                }
        return {}
    except Exception as e:
        print(f"❌ Fangraphs SP error: {e}")
        return {}

# ✅ Bullpen Fatigue
def get_bullpen_fatigue_score(team_abbr):
    try:
        url = "https://www.rotowire.com/baseball/bullpen-report.php"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.content, "html.parser")
        blocks = soup.select(".lineup")
        for block in blocks:
            abbr = block.select_one(".lineup__abbr")
            if abbr and abbr.text.strip().upper() == team_abbr.upper():
                count = sum("20" in p.text for p in block.select(".lineup__player__stats"))
                return 2.5 if count >= 3 else 1.0
        return 1.0
    except Exception as e:
        print(f"❌ Bullpen error: {e}")
        return 1.0

# ✅ Defensive Stat (DRS)
def get_team_drs(team_abbr):
    url = "https://www.fangraphs.com/leaders.aspx?pos=all&stats=fld&lg=all&qual=0&type=8&season=2025"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 6 and team_abbr.upper() in cols[1].text.strip().upper():
                return float(cols[6].text.strip())
        return 0
    except Exception as e:
        print(f"❌ DRS error: {e}")
        return 0

# ✅ SP Handedness
def get_sp_handedness(team_abbr):
    try:
        r = requests.get("https://statsapi.mlb.com/api/v1/teams?season=2025")
        teams = r.json()["teams"]
        team_id = next(t["id"] for t in teams if t["abbreviation"] == team_abbr)
        roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/active").json()["roster"]
        for p in roster:
            if p["position"]["abbreviation"] == "SP":
                pid = p["person"]["id"]
                detail = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}").json()
                return detail["people"][0]["pitchHand"]["code"]
        return "R"
    except Exception as e:
        print(f"❌ SP handedness error: {e}")
        return "R"

# ✅ Park Factor
def get_park_factor(team_abbr):
    try:
        r = requests.get("https://www.espn.com/mlb/stats/parkfactor", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3 and team_abbr.upper() in cols[0].text.strip().upper():
                return float(cols[2].text.strip())
        return 100.0
    except Exception as e:
        print(f"❌ Park factor error: {e}")
        return 100.0

# ✅ Vegas Totals (Team-split)
def get_vegas_totals(team_abbr):
    try:
        r = requests.get("https://www.vegasinsider.com/mlb/odds/las-vegas/", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        games = soup.select(".viGameScorebox")
        for game in games:
            teams = game.select(".viTeamName")
            odds = game.select(".viConsensusLine")
            if len(teams) < 2 or not odds:
                continue
            t1, t2 = teams[0].text.strip().upper(), teams[1].text.strip().upper()
            total = float(odds[0].text.strip().split()[0])
            if team_abbr.upper() in t1:
                return {"vegasTotal": total, "teamTotal": round(total * 0.55, 2)}
            elif team_abbr.upper() in t2:
                return {"vegasTotal": total, "teamTotal": round(total * 0.45, 2)}
        return {"vegasTotal": 9.0, "teamTotal": 4.5}
    except Exception as e:
        print(f"❌ Vegas odds error: {e}")
        return {"vegasTotal": 9.0, "teamTotal": 4.5}

# ✅ PA Projections
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
        return 5
    except Exception as e:
        print(f"❌ PA scrape error: {e}")
        return 5

# ✅ Run Environment Wrapper
def get_run_environment(team):
    vegas = get_vegas_totals(team)
    return {
        "parkFactor": get_park_factor(team),
        "weather": {
            "temperature": 76,
            "windSpeed": 8,
            "windDirection": "Out to LF"
        },
        "vegasTotal": vegas["vegasTotal"],
        "teamTotal": vegas["teamTotal"]
    }

# ✅ Injury Filter
def is_player_active(name):
    try:
        r = requests.get("https://www.fantasypros.com/mlb/lineups/today/", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.content, "html.parser")
        for block in soup.select(".lineup__player"):
            pname = block.select_one(".lineup__player__name")
            if pname and name.lower() in pname.text.lower():
                status = block.select_one(".lineup__player__status")
                return not (status and "inj" in status.text.lower())
        return True
    except:
        return True

# ✅ Full Audit Endpoint
@app.get("/api/v1/audit/today")
def audit_all_today_hitters():
    chadwick_map = load_chadwick_mapping()
    lineups = get_today_lineups()
    results = []

    for lineup in lineups:
        team = lineup["team"]
        for player in lineup["players"]:
            name = player["name"]
            if not is_player_active(name):
                continue

            name_key = name.lower().strip()
            mlbam_id = chadwick_map.get(name_key)
            if not mlbam_id:
                print(f"⚠️ No MLBAM ID: {name}")
                continue

            power = get_power_metrics_real(mlbam_id)
            if not power:
                continue

            opponent = get_fangraphs_sp_stats(team)
            opponent["handedness"] = get_sp_handedness(team)
            opponent["bullpenFatigueScore"] = get_bullpen_fatigue_score(team)
            opponent["teamDRS"] = get_team_drs(team)

            run_env = get_run_environment(team)
            recent = get_recent_form_real(mlbam_id)
            pitch = get_pitch_type_edge_real(mlbam_id)
            pa = get_projected_pa(name)

            results.append({
                "nam

@app.get("/openapi.yaml", include_in_schema=False)
def serve_openapi_spec():
    return FileResponse("openapi.yaml", media_type="text/yaml")
