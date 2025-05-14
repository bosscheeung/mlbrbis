import csv
import requests
from io import StringIO

def load_chadwick_mapping():
    base_url = "https://raw.githubusercontent.com/chadwickbureau/register/refs/heads/master/data/"
    suffixes = list("0123456789abcdefghijklmnopqrstuvwxyz")
    filenames = [f"people-{s}.csv" for s in suffixes]

    name_to_id = {}

    for file in filenames:
        url = base_url + file
        try:
            print(f"🔄 Downloading {file}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                print(f"⚠️  {file} not found (404), skipping.")
                continue
            response.raise_for_status()

            reader = csv.DictReader(StringIO(response.text))
            for row in reader:
                if row.get("mlbam_id"):
                    full_name = f"{row['name_first']} {row['name_last']}".lower().strip()
                    name_to_id[full_name] = row["mlbam_id"]

        except Exception as e:
            print(f"❌ Failed to load {file}: {e}")
            continue

    print(f"✅ Loaded {len(name_to_id)} MLBAM IDs from Chadwick")
    return name_to_id

# Optional: run test directly
if __name__ == "__main__":
    mapping = load_chadwick_mapping()
    print(mapping.get("ronald acuna jr"))
