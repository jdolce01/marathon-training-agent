import requests
import pandas as pd
from datetime import datetime, timedelta
import data_store

# 1. PREHAB & PHYSICAL RECOVERY ENGINE
PREHAB_EXERCISES = {
    "knee": [
        "Spanish Squats / Isometric Wall Sits (4x45s holds)",
        "Eccentric Single-Leg Step-Downs (3x10)",
        "VMO Quad Sets (3x15)"
    ],
    "it band": [
        "Side-lying Clamshells with resistance band (3x15)",
        "Standing IT Band Wall Stretch (30s hold)",
        "Lateral Band Walks (3x10/side)"
    ],
    "shin": [
        "Tibialis Wall Raises (3x20)",
        "Soleus/Gastrocnemius Eccentric Heel Drops (3x15)",
        "Toe Curls with Towel"
    ],
    "achilles": [
        "Bent-Knee Calf Stretch (Soleus bias)",
        "Golf Ball / Foam Roller Foot Arch Rolling (2 mins)",
        "Straight-Leg Eccentric Calf Drops (3x15)"
    ],
    "hip": [
        "Glute Bridges with 5-second hold (3x12)",
        "90/90 Hip Mobility Flow (2 mins/side)",
        "Monster Walks with Mini-Band"
    ]
}


def analyze_notes_for_pain(text: str) -> list:
    """Scans free-text log notes for pain keywords and returns matched areas."""
    if not text:
        return []
    text_lower = text.lower()
    detected = []
    for key in PREHAB_EXERCISES.keys():
        if key in text_lower or ("patella" in text_lower and key == "knee") or (
                "plantar" in text_lower and key == "achilles"):
            detected.append(key)
    return list(set(detected))


def get_prehab_for_keywords(keywords: list) -> dict:
    """Returns exercise lists for detected pain keywords."""
    results = {}
    for kw in keywords:
        results[kw.title()] = PREHAB_EXERCISES.get(kw, ["Foam rolling and light dynamic stretching (10 mins)"])
    return results


# 2. PACE & GOAL CALCULATOR
def calculate_target_paces(target_time_str: str) -> dict:
    """Parses HH:MM or HH:MM:SS target marathon time and returns training zones."""
    try:
        parts = list(map(int, target_time_str.split(":")))
        if len(parts) == 2:
            hours, minutes = parts[0], parts[1]
            total_mins = hours * 60 + minutes
        elif len(parts) == 3:
            hours, minutes, secs = parts[0], parts[1], parts[2]
            total_mins = hours * 60 + minutes + secs / 60.0
        else:
            total_mins = 210.0  # Default 3:30
    except Exception:
        total_mins = 210.0

    marathon_pace_sec = (total_mins * 60) / 26.2

    def fmt_pace(sec):
        m, s = divmod(int(sec), 60)
        return f"{m}:{s:02d}/mi"

    return {
        "Goal Marathon Pace (MP)": fmt_pace(marathon_pace_sec),
        "Easy / Recovery Pace": f"{fmt_pace(marathon_pace_sec + 60)} - {fmt_pace(marathon_pace_sec + 90)}",
        "Tempo / Threshold Pace": f"{fmt_pace(marathon_pace_sec - 25)} - {fmt_pace(marathon_pace_sec - 15)}",
        "Interval / VO2 Max Pace": f"{fmt_pace(marathon_pace_sec - 50)} - {fmt_pace(marathon_pace_sec - 40)}"
    }


# 3. STRUCTURED POPULAR WORKOUT RECOMMENDATIONS
def get_suggested_workouts(weekly_target: float) -> list:
    """Generates classic marathon training workouts scaled to current volume build."""
    long_run = round(min(weekly_target * 0.35, 20.0), 1)
    tempo_miles = round(max(3.0, weekly_target * 0.12), 1)

    return [
        {
            "name": "Pfitz Tempo Run",
            "type": "Threshold",
            "desc": f"2 mi Easy Warmup + {tempo_miles} mi @ Tempo/Threshold Pace + 1.5 mi Cool Down."
        },
        {
            "name": "Yasso 800s (VO2 Max)",
            "type": "Intervals",
            "desc": "6-8 x 800m @ VO2 Max Pace with equal time active recovery jog between reps."
        },
        {
            "name": "Progression Long Run",
            "type": "Long Run",
            "desc": f"{long_run} mi total: First {round(long_run * 0.6, 1)} mi @ Easy Pace, final {round(long_run * 0.4, 1)} mi progression down to Goal Marathon Pace."
        }
    ]


# 4. WEATHER ALERT TOOL
def get_weather_alert(latitude: float = 39.8912, longitude: float = -75.0377) -> str:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=precipitation_probability,temperature_2m&temperature_unit=fahrenheit&timezone=auto"
    try:
        res = requests.get(url, timeout=5).json()
        hourly = res.get("hourly", {})
        times = hourly.get("time", [])
        precip = hourly.get("precipitation_probability", [])

        tomorrow_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_rain_probs = []

        for t, p in zip(times, precip):
            if t.startswith(tomorrow_date_str):
                hour = int(t.split("T")[1].split(":")[0])
                if 6 <= hour <= 9:
                    tomorrow_rain_probs.append(p)

        formatted_date = (datetime.now() + timedelta(days=1)).strftime("%A, %b %d")

        if tomorrow_rain_probs and any(p > 40 for p in tomorrow_rain_probs):
            max_prob = max(tomorrow_rain_probs)
            return f"🌧️ **Weather Alert for Tomorrow ({formatted_date}):** High rain probability ({max_prob}%) forecasted tomorrow morning (6:00-9:00 AM). Consider shifting your run window or moving indoors."
        return f"☀️ **Weather Clear for Tomorrow ({formatted_date}):** Morning conditions look clear (low rain risk) for your scheduled run!"
    except Exception:
        return "Weather forecast currently unavailable."


# 5. ZERO-FILLED DATE RANGE DATAFRAME GENERATOR
def get_zero_filled_df():
    """Returns logs dataframe reindexed across a complete date sequence with 0s for missing days."""
    df = data_store.get_logs_df()
    if df.empty:
        return df

    df['log_date'] = pd.to_datetime(df['log_date'])
    min_date = df['log_date'].min()
    max_date = max(df['log_date'].max(), pd.to_datetime(datetime.now().date()))

    full_idx = pd.date_range(start=min_date, end=max_date, freq='D')
    df = df.set_index('log_date').reindex(full_idx)
    df.index.name = 'log_date'

    df['distance_miles'] = df['distance_miles'].fillna(0.0)
    df['cross_train_mins'] = df['cross_train_mins'].fillna(0)
    df['effective_miles'] = df['distance_miles'] + (df['cross_train_mins'] / 10.0)
    df['notes'] = df['notes'].fillna("")
    df['leg_soreness'] = df['leg_soreness'].fillna(1)

    return df.reset_index()


def calculate_progressive_build() -> float:
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