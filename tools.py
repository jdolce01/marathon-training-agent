import requests
import pandas as pd
from datetime import datetime, timedelta
import data_store

# 1. PREHAB & PHYSICAL RECOVERY ENGINE
PREHAB_EXERCISES = {
    "knee_patellar": [
        "Spanish Squats / Isometric Wall Sits (4x45s holds)",
        "Eccentric Single-Leg Step-Downs (3x10)",
        "VMO Quad Sets (3x15)"
    ],
    "it_band": [
        "Side-lying Clamshells with resistance band (3x15)",
        "Standing IT Band Wall Stretch (30s hold)",
        "Lateral Band Walks (3x10/side)"
    ],
    "shin_splints": [
        "Tibialis Wall Raises (3x20)",
        "Soleus/Gastrocnemius Eccentric Heel Drops (3x15)",
        "Toe Curls with Towel"
    ],
    "achilles_plantar": [
        "Bent-Knee Calf Stretch (Soleus bias)",
        "Golf Ball / Foam Roller Foot Arch Rolling (2 mins)",
        "Straight-Leg Eccentric Calf Drops"
    ]
}


def get_prehab_exercises(pain_location: str) -> list:
    """Returns specific mobility & strength exercises based on reported pain."""
    if not pain_location or pain_location == "None":
        return ["Perform 10 mins of general foam rolling (quads, calves, glutes)."]

    key = pain_location.lower().replace(" ", "_")
    for k in PREHAB_EXERCISES:
        if k in key:
            return PREHAB_EXERCISES[k]
    return ["Foam roll quads, hamstrings, and calves (10 mins)", "Light dynamic mobility flow"]


# 2. ACCURATE WEATHER FORECAST TOOL WITH DATES
def get_weather_alert(latitude: float = 39.8912, longitude: float = -75.0377) -> str:
    """Fetches hourly weather for TOMORROW morning specifically."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=precipitation_probability,temperature_2m&temperature_unit=fahrenheit&timezone=auto"
    try:
        res = requests.get(url, timeout=5).json()
        hourly = res.get("hourly", {})
        times = hourly.get("time", [])
        precip = hourly.get("precipitation_probability", [])

        tomorrow_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_rain_probs = []

        # Filter weather entries specifically for tomorrow between 06:00 and 09:00
        for t, p in zip(times, precip):
            if t.startswith(tomorrow_date_str):
                hour = int(t.split("T")[1].split(":")[0])
                if 6 <= hour <= 9:
                    tomorrow_rain_probs.append(p)

        formatted_date = (datetime.now() + timedelta(days=1)).strftime("%A, %b %d")

        if tomorrow_rain_probs and any(p > 40 for p in tomorrow_rain_probs):
            max_prob = max(tomorrow_rain_probs)
            return f"🌧️ **Weather Alert for Tomorrow ({formatted_date}):** High rain probability ({max_prob}%) forecasted tomorrow morning between 6:00 AM and 9:00 AM. Consider shifting your run window or moving indoors."
        return f"☀️ **Weather Clear for Tomorrow ({formatted_date}):** Morning conditions look clear (low rain risk) for your scheduled run!"
    except Exception:
        return "Weather forecast currently unavailable."


# 3. HIGH-BASELINE PROGRESSIVE VOLUME SCALER
def calculate_progressive_build() -> float:
    """
    Calculates weekly target using max recent weekly volume or baseline setting,
    applying a strict 10% progression rule.
    """
    df = data_store.get_logs_df()
    saved_baseline = float(data_store.get_setting("baseline_mileage", "35.0"))

    if not df.empty:
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        weekly_totals = df.groupby('Week')['distance_miles'].sum()
        if not weekly_totals.empty:
            recent_max = weekly_totals.tail(3).max()
            base = max(recent_max, saved_baseline)
            return round(base * 1.10, 1)

    return round(saved_baseline * 1.10, 1)