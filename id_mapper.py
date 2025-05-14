import csv
import json
import os
import requests
from io import StringIO
import re

CACHE_FILE = "mlbam_cache.json"

def normalize_name(name):
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def load_chadwick_mapping():
    # ✅ Use cache if available
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            print("✅ Loaded MLBAM cache from file.")
            return json.load(f)

    base_url = "https://raw.githubusercontent.com/chadwickbureau/register/refs/heads/master/data/"
    suffixes = list("0123456789abcdefghijklmnopqrstuvwxyz")
    filenames = [f"people-{s}.csv" for s in suffixes]

    name_to_id = {}
    total_rows = 0

    for file in filenames:
        url = base_url + file
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200 or "html" in response.headers.get("Content-Type", ""):
                print(f"⚠️ Skipping {file}: not a valid CSV")
                continue

            reader = csv.DictReader(StringIO(response.text))
            if not {"key_mlbam", "name_first", "name_last"}.issubset(reader.fieldnames):
                print(f"⚠️ Skipping {file}: missing expected columns.")
                continue

            for row in reader:
                total_rows += 1
                if row.get("key_mlbam") and row["key_mlbam"].strip():
                    full_name = normalize_name(f"{row['name_first']} {row['name_last']}")
                    name_to_id[full_name] = row["key_mlbam"]

        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
            continue

    print(f"✅ Loaded {len(name_to_id)} MLBAM IDs from {total_rows} rows")

    # Save to cache
    with open(CACHE_FILE, "w") as f:
        json.dump(name_to_id, f)
        print("💾 Saved to mlbam_cache.json")

    return name_to_id

# Local test
if __name__ == "__main__":
    ids = load_chadwick_mapping()
    print("ronald acuna jr →", ids.get(normalize_name("ronald acuna jr")))
