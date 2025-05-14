import csv
import requests
from io import StringIO
import re

def normalize_name(name):
    # Remove common suffixes and standardize name
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"[^a-z\s]", "", name)  # remove punctuation
    name = re.sub(r"\s+", " ", name)  # clean up extra spaces
    return name.strip()

def load_chadwick_mapping():
    base_url = "https://raw.githubusercontent.com/chadwickbureau/register/refs/heads/master/data/"
    suffixes = list("0123456789abcdefghijklmnopqrstuvwxyz")
    filenames = [f"people-{s}.csv" for s in suffixes]

    name_to_id = {}
    total_rows = 0

    for file in filenames:
        url = base_url + file
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                continue
            response.raise_for_status()

            reader = csv.DictReader(StringIO(response.text))
            if not {"mlbam_id", "name_first", "name_last"}.issubset(reader.fieldnames):
                print(f"⚠️ Skipping {file}: missing required columns.")
                continue

            for row in reader:
                total_rows += 1
                if row.get("mlbam_id") and row["mlbam_id"].strip() != "":
                    full_name = normalize_name(f"{row['name_first']} {row['name_last']}")
                    name_to_id[full_name] = row["mlbam_id"]

        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
            continue

    print(f"✅ Loaded {len(name_to_id)} MLBAM IDs from {total_rows} rows")
    return name_to_id

# Test endpoint
if __name__ == "__main__":
    mapping = load_chadwick_mapping()
    print("ronald acuna jr →", mapping.get(normalize_name("ronald acuna jr")))
    print("shohei ohtani →", mapping.get(normalize_name("shohei ohtani")))
