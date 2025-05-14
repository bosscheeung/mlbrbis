from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lineup_scraper import get_today_lineups
from id_mapper import load_chadwick_mapping

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/audit/today")
def audit_all_today_hitters():
    chadwick_map = load_chadwick_mapping()
    lineups = get_today_lineups()
    
    results = []
    for team_lineup in lineups:
        team = team_lineup["team"]
        for player in team_lineup["players"]:
            name = player["name"]
            slot = player["slot"]
            mlbamId = chadwick_map.get(name.lower())
            if not mlbamId:
                continue
            # In production, you'd call each audit function here
            results.append({
                "name": name,
                "team": team,
                "mlbamId": mlbamId,
                "slot": slot,
                "audit": {
                    "powerSignal": {"barrelRate": 12.3},
                    "volumeOpportunity": {"projectedPAs": 5},
                    "opponentWeakness": {"xERA": 4.1},
                    "runEnvironment": {"vegasTotal": 9.5},
                    "recentForm": {"xSLGDeltaLast10": 0.033},
                    "pitchEdge": {"mmFastballPercent": 8.2}
                }
            })
    return results

@app.get("/openapi.yaml", include_in_schema=False)
def serve_openapi_spec():
    return FileResponse("openapi.yaml", media_type="text/yaml")

