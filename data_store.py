import json
import os
import pandas as pd

DATA_FILE = "training_logs.json"
PROFILE_FILE = "user_profile.json"

def load_profile():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    return {"marathon_date": "2026-11-01", "target_peak_mileage": 65}

def save_profile(profile_data):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile_data, f, indent=2)

def load_logs():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return pd.DataFrame(data)
    return pd.DataFrame(columns=[
        "date", "planned_miles", "actual_miles", "time_of_day", 
        "temp_f", "humidity_pct", "legs_rating", "overall_feeling", "notes"
    ])

def save_log_entry(entry_dict):
    df = load_logs()
    # Replace existing entry for same date or append
    if not df.empty and entry_dict["date"] in df["date"].values:
        df = df[df["date"] != entry_dict["date"]]
    df = pd.concat([df, pd.DataFrame([entry_dict])], ignore_index=True)
    df.to_json(DATA_FILE, orient="records", indent=2)
