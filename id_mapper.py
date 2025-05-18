import csv
import json
import os
import requests
import re
from io import StringIO

CACHE_FILE = "mlbam_cache.json"

def normalize_name(name):
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def load_chadwick_mapping():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    base_url = "https://raw.githubusercontent.com/chadwickbureau/register/refs/heads/master/data/"
    suffixes = list("0123456789abcdefghijklmnopqrstuvwxyz")
    filenames = [f"people-{s}.csv" for s in suffixes]

    name_to_id = {}

    for file in filenames:
        url = base_url + file
        try:
            res = requests.get(url, timeout=10)
            if "html" in res.headers.get("Content-Type", ""):
                continue
            reader = csv.DictReader(StringIO(res.text))
            if not {"key_mlbam", "name_first", "name_last"}.issubset(reader.fieldnames):
                continue
            for row in reader:
                if row.get("key_mlbam"):
                    full_name = normalize_name(f"{row['name_first']} {row['name_last']}")
                    name_to_id[full_name] = row["key_mlbam"]
        except:
            continue

    with open(CACHE_FILE, "w") as f:
        json.dump(name_to_id, f)

    return name_to_id
