import csv
import requests
from io import StringIO

CHADWICK_BASE_URL = "https://raw.githubusercontent.com/chadwickbureau/register/master/csv/"
CHADWICK_PARTS = [f"people-{x}.csv" for x in list("0123456789abcdefghijklmnopqrstuvwxyz")]

def load_chadwick_mapping():
    name_to_id = {}

    for filename in CHADWICK_PARTS:
        url = CHADWICK_BASE_URL + filename
        try:
            print(f"🔄 Fetching {filename}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)
            for row in reader:
                if row.get("mlbam_id"):
                    full_name = f"{row['name_first']} {row['name_last']}".lower().strip()
                    name_to_id[full_name] = row["mlbam_id"]
        except Exception as e:
            print(f"❌ Failed to fetch {filename}: {e}")

    print(f"✅ Loaded {len(name_to_id)} MLBAM IDs from Chadwick.")
    return name_to_id
