import csv
import requests
from io import StringIO

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
                print(f"⚠️ Skipping {file}: missing expected columns.")
                continue

            for row in reader:
                total_rows += 1
                if row.get("mlbam_id") and row["mlbam_id"] != "":
                    full_name = f"{row['name_first']} {row['name_last']}".lower().strip()
                    name_to_id[full_name] = row["mlbam_id"]

        except Exception as e:
            print(f"❌ Error loading {file}: {e}")

    print(f"✅ Loaded {len(name_to_id)} MLBAM IDs from {total_rows} rows")
    return name_to_id
