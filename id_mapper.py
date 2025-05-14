import csv
import json
import os
import re
import requests
from io import StringIO

CACHE_FILE = "mlbam_cache.json"

def normalize_name(name):
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def load_chadwick_mapping():
    print("🔍 load_chadwick_mapping() called")

    if os.path.exists(CACHE_FILE):
        print("✅ Loaded MLBAM cache from file.")
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

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

            content_type = res.headers.get("Content-Type", "")
            if res.status_code != 200 or "html" in content_type:
                print(f"⚠️ Skipping {file}: invalid content (status {res.status_code}, type {content_type})")
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

            print(f"✅ Parsed {file}: {len(name_to_id)} IDs collected so far.")

        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
            continue

    print(f"✅ Finished loading. Total IDs: {len(name_to_id)} from {total_rows} rows.")

    with open(CACHE_FILE, "w") as f:
        json.dump(name_to_id, f)
        print("💾 Saved ID map to mlbam_cache.json")

    return name_to_id

# Optional manual test
if __name__ == "__main__":
    ids = load_chadwick_mapping()
    print("ronald acuna jr →", ids.get(normalize_name("ronald acuna jr")))
    print("shohei ohtani →", ids.get(normalize_name("shohei ohtani")))
