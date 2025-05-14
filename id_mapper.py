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
    # ✅ Step 1: Load cache if it exists
    if os.path.exists(CACHE_FILE):
        print("✅ Loading from cache...")
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    # ✅ Step 2: Attempt to fetch raw CSVs from GitHub
    base_url = "https://raw.githubusercontent.com/chadwickbureau/register/refs/heads/master/data/"
    suffixes = list("0123456789abcdefghijklmnopqrstuvwxyz")
    filenames = [f"people-{s}.csv" for s in suffixes]

    name_to_id = {}
    total_rows = 0

    for file in filenames:
        url = base_url + file
        try:
            print(f"🔄 Fetching {file} ...")
            res = requests.get(url, timeout=10)

            # Log and skip invalid files
            content_type = res.headers.get("Content-Type", "unknown")
            if res.status_code != 200:
                print(f"⚠️ {file} status {res.status_code}, skipping.")
                continue
            if "html" in content_type:
                print(f"⚠️ {file} returned HTML, skipping.")
                continue

            reader = csv.DictReader(StringIO(res.text))
            if not {"key_mlbam", "name_first", "name_last"}.issubset(reader.fieldnames):
                print(f"⚠️ {file} missing required columns: {reader.fieldnames}")
                continue

            for row in reader:
                total_rows += 1
                if row.get("key_mlbam") and row["key_mlbam"].strip():
                    full_name = normalize_name(f"{row['name_first']} {row['name_last']}")
                    name_to_id[full_name] = row["key_mlbam"]

            print(f"✅ Parsed {file} with {len(name_to_id)} IDs so far.")

        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
            continue

    print(f"✅ Finished: {len(name_to_id)} MLBAM IDs loaded from {total_rows} rows.")

    with open(CACHE_FILE, "w") as f:
        json.dump(name_to_id, f)
        print("💾 Cache saved to mlbam_cache.json")

    return name_to_id

# Manual test
if __name__ == "__main__":
    mapping = load_chadwick_mapping()
    print("ronald acuna jr →", mapping.get(normalize_name("ronald acuna jr")))
