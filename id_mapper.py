import csv

def load_chadwick_mapping(filepath="register.csv"):
    name_to_id = {}
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row["name_last"] + ", " + row["name_first"]
            full_name = name.replace(",", "").strip().lower()
            name_to_id[full_name] = row["mlbam_id"]
    return name_to_id
