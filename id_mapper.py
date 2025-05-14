import csv
import requests
from io import StringIO
import re

def normalize_name(name):
    # Remove suffixes like Jr, Sr, III, etc. and standardize
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"[^a-z\s]", "", name)  # remove punctuation
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def load_chadwick_mapping():
    base_url = "https://raw.githubusercontent.com/chadwickbureau/register/master/csv/"
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
            if not {"key_mlbam", "name_first", "name_last"}.issubset(reader.fieldnames):
                print(f"⚠️ Skipping {file}: missing expected columns.")
                continue

            for row in reader:
                total_rows += 1
                if row.get("key_mlbam") and row["key_mlbam"].strip() != "":
                    full_name = normalize_name(f"{row['name_first']} {row['name_last']}")
                    name_to_id[full_name] = row["key_mlbam"]

        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
            continue

    print(f"✅ Loaded {len(name_to_id)} MLBAM IDs from {total_rows} rows")
    return name_to_id

# ✅ Test locally
if __name__ == "__main__":
    mapping = load_chadwick_mapping()
    test_names = [
        "ronald acuna jr",
        "shohei ohtani",
        "mookie betts",
        "matt olson"
    ]
    for name in test_names:
        print(f"{name} → {mapping.get(normalize_name(name))}")
