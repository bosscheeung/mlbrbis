from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from id_mapper import load_chadwick_mapping
from lineup_scraper import get_today_lineups
import requests
from bs4 import BeautifulSoup
from io import StringIO
import csv

app = FastAPI()

# Enable CORS so GPT can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
        print(f"❌ Power data error for {mlbam_id}: {e}")
        return None
def get_fangraphs_sp_stats(team_name):
    url = "https://www.fangraphs.com/leaders.aspx?pos=all&stats=pit&lg=all&qual=10&type=1&season=2025"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", {"class": "rgMasterTable"})

        if not table:
            return {}

        rows = table.find_all("tr")[1:]

        for row in rows:
            cells = row.find_all("td")
            if not cells or len(cells) < 12:
                continue

            team_cell = cells[2].text.strip().upper()
            if team_cell == team_name.upper():
                return {
                    "xERA": float(cells[11].text.strip()),
                    "hrPer9": float(cells[8].text.strip())
                }

        return {}
    except Exception as e:
        print(f"❌ Fangraphs error: {e}")
        return {}
def get_bullpen_fatigue_score(team_abbr):
    url = "https://www.rotowire.com/baseball/bullpen-report.php"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, "html.parser")
        blocks = soup.select(".lineup.is-confirmed, .lineup")

        for block in blocks:
            abbr = block.select_one(".lineup__abbr")
            if abbr and abbr.text.strip().upper() == team_abbr.upper():
                count = 0
                for p in block.select(".lineup__player__stats"):
                    if "20" in p.text:
                        count += 1
                return 2.5 if count >= 3 else 1.0

        return 1.0
    except Exception as e:
        print(f"❌ RotoWire error: {e}")
        return 1.0
def get_opponent_weakness_real(team):
    stats = get_fangraphs_sp_stats(team)
    return {
        "handedness": "R",
        "xERA": stats.get("xERA", 4.25),
        "hrPer9": stats.get("hrPer9", 1.3),
        "bullpenFatigueScore": get_bullpen_fatigue_score(team)
    }
def get_park_factor(team_abbr):
    url = "https://www.espn.com/mlb/stats/parkfactor"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                team = cols[0].text.strip().upper()
                factor = cols[2].text.strip()
                if team_abbr.upper() in team:
                    return float(factor)

        return 100.0
    except Exception as e:
        print(f"❌ ESPN park factor error: {e}")
        return 100.0
def get_vegas_totals(team_abbr):
    url = "https://www.vegasinsider.com/mlb/odds/las-vegas/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        games = soup.select(".viGameScorebox")

        for game in games:
            teams = game.select(".viTeamName")
            odds = game.select(".viConsensusLine")

            if len(teams) < 2 or len(odds) < 1:
                continue

            team1 = teams[0].text.strip().upper()
            team2 = teams[1].text.strip().upper()
            total = odds[0].text.strip()

            if team_abbr.upper() in team1 or team_abbr.upper() in team2:
                try:
                    vegas_total = float(total.split()[0])
                except:
                    vegas_total = 9.0
                return {
                    "vegasTotal": vegas_total,
                    "teamTotal": round(vegas_total / 2, 2)
                }

        return {"vegasTotal": 9.0, "teamTotal": 4.5}
    except Exception as e:
        print(f"❌ Vegas odds error: {e}")
        return {"vegasTotal": 9.0, "teamTotal": 4.5}
def get_run_environment_live(team):
    vegas = get_vegas_totals(team)
    return {
        "parkFactor": get_park_factor(team),
        "weather": {
            "temperature": 76,
            "windSpeed": 9,
            "windDirection": "Out to LF"
        },
        "vegasTotal": vegas["vegasTotal"],
        "teamTotal": vegas["teamTotal"]
    }
from savant_scraper import get_pitch_type_edge_real, get_recent_form_real
def get_projected_pa(name):
    url = "https://www.fangraphs.com/projections?pos=all&stats=bat&type=fangraphsdc"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr")
        clean_name = name.lower().replace(".", "").replace(" jr", "").strip()

        for row in rows:
            cols = row.find_all("td")
            if not cols or len(cols) < 6:
                continue

            player_name = cols[0].text.strip().lower().replace(".", "").replace(" jr", "").strip()
            if clean_name in player_name or player_name in clean_name:
                try:
                    pa = int(cols[5].text.strip())
                    return pa
                except:
                    return None

        return None
    except Exception as e:
        print(f"❌ PA scrape error: {e}")
        return None
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
                print(f"⚠️ No MLBAM ID for: {name}")
                continue

            power = get_power_metrics_real(mlbam_id)
            if not power:
                continue

            opponent = get_opponent_weakness_real(team)
            run_env = get_run_environment_live(team)
            recent = get_recent_form_real(mlbam_id)
            pitch = get_pitch_type_edge_real(mlbam_id)
            projected_pa = get_projected_pa(name) or 5

            results.append({
                "name": name,
                "team": team,
                "mlbamId": mlbam_id,
                "slot": player["slot"],
                "audit": {
                    "powerSignal": power,
                    "volumeOpportunity": {
                        "slot": player["slot"],
                        "projectedPAs": projected_pa
                    },
                    "opponentWeakness": opponent,
                    "runEnvironment": run_env,
                    "recentForm": recent,
                    "pitchEdge": pitch
                }
            })

    return results
