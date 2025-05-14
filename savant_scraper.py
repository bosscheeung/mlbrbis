from playwright.sync_api import sync_playwright
import json

def get_savant_json_blob(mlbam_id):
    url = f"https://baseballsavant.mlb.com/savant-player?id={mlbam_id}&type=batter"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30000)

        content = page.content()
        browser.close()

        # Find JSON embedded in <script> tags
        start_marker = "window.__INITIAL_DATA__ = "
        end_marker = ";</script>"

        try:
            start = content.index(start_marker) + len(start_marker)
            end = content.index(end_marker, start)
            raw_json = content[start:end].strip()
            data = json.loads(raw_json)
            return data
        except Exception as e:
            print(f"❌ Failed to extract JSON for MLBAM {mlbam_id}: {e}")
            return None
def get_recent_form_real(mlbam_id):
    data = get_savant_json_blob(mlbam_id)
    if not data:
        return {"xSLGDeltaLast10": 0.0, "multiRBIGames": 0}

    try:
        gamelog = data["player"]["stats"]["gameLog"]
        recent_games = gamelog[-10:]

        xslg_total = sum(g.get("xslg", 0) for g in recent_games)
        xslg_10_avg = xslg_total / len(recent_games)

        season_xslg = data["player"]["stats"]["summary"]["xslg"]
        delta = round(xslg_10_avg - season_xslg, 3)

        multi_rbi_games = sum(1 for g in recent_games if g.get("rbi", 0) >= 2)

        return {
            "xSLGDeltaLast10": delta,
            "multiRBIGames": multi_rbi_games
        }
    except Exception as e:
        print(f"❌ Error in recent form parse: {e}")
        return {"xSLGDeltaLast10": 0.0, "multiRBIGames": 0}
def get_pitch_type_edge_real(mlbam_id):
    data = get_savant_json_blob(mlbam_id)
    if not data:
        return {
            "xwOBA": {},
            "mmFastballPercent": 0.0
        }

    try:
        arsenal = data["player"]["pitchArsenal"]
        xwoba = {}
        mm_percent = 0.0

        for pitch in arsenal:
            pitch_type = pitch.get("pitchType")
            xwoba_value = pitch.get("xwoba", 0)
            if pitch_type and xwoba_value:
                xwoba[pitch_type] = round(xwoba_value, 3)

            if pitch.get("zone") == "Middle-Middle" and "Fastball" in pitch_type:
                mm_percent = pitch.get("usage", 0)

        return {
            "xwOBA": xwoba,
            "mmFastballPercent": mm_percent
        }

    except Exception as e:
        print(f"❌ Pitch edge parse error: {e}")
        return {
            "xwOBA": {},
            "mmFastballPercent": 0.0
        }
