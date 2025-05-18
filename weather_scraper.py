import requests
from bs4 import BeautifulSoup
import re

def get_weather_scrape(team_abbr):
    try:
        url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=today"
        schedule = requests.get(url).json()

        for game in schedule.get("dates", [])[0].get("games", []):
            teams = game.get("teams", {})
            for side in ["home", "away"]:
                info = teams.get(side, {}).get("team", {})
                if info.get("abbreviation", "").upper() == team_abbr.upper():
                    preview_url = f"https://www.mlb.com{game.get('content', {}).get('link', '')}"
                    page = requests.get(preview_url).text
                    soup = BeautifulSoup(page, "html.parser")
                    text = soup.get_text()
                    return parse_weather_string(text)
    except:
        pass

    return {
        "temperature": 75,
        "windSpeed": 8,
        "windDirection": "Unknown"
    }

def parse_weather_string(text):
    temp_match = re.search(r"(\d{2,3}) ?°F", text)
    wind_match = re.search(r"Wind:? (\d{1,2}) mph (Out|In|Left|Right|Center|to [A-Z]+)", text, re.IGNORECASE)

    return {
        "temperature": int(temp_match.group(1)) if temp_match else 75,
        "windSpeed": int(wind_match.group(1)) if wind_match else 8,
        "windDirection": wind_match.group(2) if wind_match else "Unknown"
    }
