from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from id_mapper import load_chadwick_mapping, normalize_name
from savant_scraper import get_power_metrics

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
    return {"status": "API is live"}

@app.get("/api/v1/debug/ids")
def get_mlbam_id(name: str):
    chadwick = load_chadwick_mapping()
    key = normalize_name(name)
    mlbam_id = chadwick.get(key)
    return {
        "input": name,
        "normalized": key,
        "mlbamId": mlbam_id
    }

@app.get("/api/v1/debug/power")
def get_power(name: str):
    chadwick = load_chadwick_mapping()
    key = normalize_name(name)
    mlbam_id = chadwick.get(key)
    if not mlbam_id:
        return {
            "error": f"MLBAM ID not found for '{name}'",
            "normalized": key
        }
    power = get_power_metrics(mlbam_id)
    return {
        "name": name,
        "mlbamId": mlbam_id,
        "powerSignal": power or "not found"
    }
