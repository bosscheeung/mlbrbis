from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open to ChatGPT calls
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/identifiers")
def get_player_identifiers(playerName: str):
    return {
        "mlbamId": "123456",
        "fangraphsId": "654321",
        "espnId": "789012"
    }

@app.get("/api/v1/lineup-slot")
def get_lineup_slot(mlbamId: str):
    return {"slot": "2"}

@app.get("/api/v1/pa-projection")
def get_pa_projection(mlbamId: str):
    return {"projectedPAs": 5}

@app.get("/api/v1/power-metrics")
def get_power_metrics(mlbamId: str):
    return {
        "barrelRate": 13.2,
        "xSLG": 0.470,
        "hardHitPercent": 44.1,
        "avgExitVelocity": 91.0
    }

@app.get("/api/v1/opponent-starter")
def get_opponent_starter_metrics(team: str):
    return {
        "handedness": "R",
        "xERA": 3.92,
        "hrPer9": 1.3
    }

@app.get("/api/v1/bullpen-fatigue")
def get_bullpen_fatigue(team: str):
    return {"fatigueScore": 2.4}

@app.get("/api/v1/park-weather-vegas")
def get_park_weather_vegas(gameId: str):
    return {
        "parkFactor": 102,
        "weather": {
            "temperature": 75,
            "windSpeed": 8,
            "windDirection": "Out to left"
        },
        "vegasTotal": 9.0,
        "teamTotal": 4.7
    }

@app.get("/api/v1/recent-form")
def get_recent_form_metrics(mlbamId: str):
    return {
        "xSLGDeltaLast10": 0.038,
        "multiRBIGames": 3
    }

@app.get("/api/v1/pitch-type-edge")
def get_pitch_type_edge(mlbamId: str):
    return {
        "xwOBA": {
            "Fastball": 0.310,
            "Slider": 0.278,
            "Curveball": 0.250
        },
        "mmFastballPercent": 7.9
    }
