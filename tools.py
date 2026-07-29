import requests
import pandas as pd
import re
from datetime import datetime, timedelta
import data_store


# 1. HEART RATE ZONE CALCULATOR (Karvonen Method)
def calculate_hr_zones(max_hr: int, resting_hr: int) -> dict:
    hrr = max_hr - resting_hr
    return {
        "Zone 1 (Active Recovery)": f"{round(resting_hr + hrr * 0.50)} - {round(resting_hr + hrr * 0.60)} bpm",
        "Zone 2 (Aerobic / Easy Run)": f"{round(resting_hr + hrr * 0.60)} - {round(resting_hr + hrr * 0.70)} bpm",
        "Zone 3 (Marathon Pace)": f"{round(resting_hr + hrr * 0.70)} - {round(resting_hr + hrr * 0.80)} bpm",
        "Zone 4 (Threshold / Tempo)": f"{round(resting_hr + hrr * 0.80)} - {round(resting_hr + hrr * 0.90)} bpm",
        "Zone 5 (VO2 Max / Intervals)": f"{round(resting_hr + hrr * 0.90)} - {max_hr} bpm"
    }


# 2. FRAMEWORK-SPECIFIC WORKOUT GENERATOR
def get_framework_workouts(weekly_target: float, framework: str, elevation: str) -> list:
    hill_note = " (Include 150-200ft elevation gain for hilly course prep)" if "Hilly" in elevation else ""

    if framework == "Pfitzinger (Pfitz)":
        long_run = round(min(weekly_target * 0.35, 20.0), 1)
        mid_long = round(min(weekly_target * 0.22, 12.0), 1)
        tempo = round(max(3.0, weekly_target * 0.12), 1)
        return [
            {"name": "Pfitz Mid-Week Medium-Long Run", "type": "Aerobic Build",
             "desc": f"{mid_long} miles @ Easy/Aerobic pace. Crucial for building endurance without weekend fatigue.{hill_note}"},
            {"name": "Pfitz Lactate Threshold Run", "type": "Threshold",
             "desc": f"2 mi warmup + {tempo} mi @ LT Pace + 1.5 mi cooldown."},
            {"name": "Pfitz Long Run", "type": "Long Run",
             "desc": f"{long_run} miles steady effort, building to marathon pace in the last 4 miles.{hill_note}"}
        ]
    elif framework == "Hanson Method":
        long_run = round(min(weekly_target * 0.30, 16.0), 1)
        mp_run = round(min(weekly_target * 0.20, 10.0), 1)
        return [
            {"name": "Hanson Marathon Pace (MP) Run", "type": "Quality",
             "desc": f"2 mi warmup + {mp_run} mi @ Goal Marathon Pace + 1 mi cooldown."},
            {"name": "Hanson Strength Intervals", "type": "Threshold",
             "desc": "3 x 2 miles @ 10s faster than MP with 800m recovery jog."},
            {"name": "Hanson Cumulative Fatigue Long Run", "type": "Long Run",
             "desc": f"{long_run} miles max. Designed to be run on tired legs after mid-week quality.{hill_note}"}
        ]
    else:  # Jack Daniels
        long_run = round(min(weekly_target * 0.33, 20.0), 1)
        tempo = round(max(3.0, weekly_target * 0.10), 1)
        return [
            {"name": "Daniels Threshold (T) Cruise Intervals", "type": "Threshold",
             "desc": f"4 x 1 mile @ Threshold Pace with 1 min rest between reps."},
            {"name": "Daniels Interval (I) VO2 Max", "type": "Speed",
             "desc": "5 x 1000m @ I-Pace with 3 min jog recovery."},
            {"name": "Daniels Quality Long Run (2Q)", "type": "Long Run",
             "desc": f"{long_run} miles total: 4 mi Easy + {tempo} mi @ Threshold + 2 mi Easy + finish steady.{hill_note}"}
        ]


# 3. HOURLY WEATHER FORECAST
def get_detailed_weather_forecast(latitude: float = 39.8912, longitude: float = -75.0377) -> dict:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=precipitation_probability,temperature_2m,relative_humidity_2m&temperature_unit=fahrenheit&timezone=auto"
    try:
        res = requests.get(url, timeout=5).json()
        hourly = res.get("hourly", {})
        times = hourly.get("time", [])
        precip = hourly.get("precipitation_probability", [])
        temps = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])

        tomorrow_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        morning_slots = []
        for t, p, temp, hum in zip(times, precip, temps, humidity):
            if t.startswith(tomorrow_date_str):
                hour = int(t.split("T")[1].split(":")[0])
                if 6 <= hour <= 9:
                    morning_slots.append({"time": f"{hour}:00 AM", "temp": round(temp), "humidity": hum, "precip": p})

        return {"date_str": (datetime.now() + timedelta(days=1)).strftime("%A, %b %d"), "slots": morning_slots}
    except Exception:
        return {"date_str": "Tomorrow", "slots": []}


# 4. NLP PAIN EXTRACTION
def analyze_notes_for_pain(text: str) -> list:
    if not text: return []
    text_lower = text.lower()
    keywords = ["knee", "patellar", "it band", "shin", "achilles", "hip", "quad", "hamstring"]
    return [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)]


def get_prehab_for_keywords(keywords: list) -> dict:
    exercises = {
        "knee": ["Spanish Squats (4x45s holds)", "Single-Leg Step-Downs (3x10)", "VMO Quad Sets"],
        "patellar": ["Single-leg decline squats (3x10)", "Foam roll quads and IT band"],
        "it band": ["Clamshells with band (3x15)", "Standing IT Band Stretch", "Lateral Band Walks"],
        "shin": ["Tibialis Wall Raises (3x20)", "Eccentric Heel Drops (3x15)", "Towel Curls"],
        "achilles": ["Soleus Calf Stretch", "Eccentric Calf Drops (3x15)", "Golf Ball Foot Arch Roll"],
        "hip": ["Glute Bridges with 5s hold (3x12)", "90/90 Hip Flow", "Monster Walks"]
    }
    return {kw.title(): exercises.get(kw, ["10 mins general foam rolling and dynamic stretching"]) for kw in keywords}


# 5. PERIODIZED VOLUME CALCULATOR
def calculate_periodized_target(weeks_ahead: int = 0) -> float:
    baseline = float(data_store.get_setting("baseline_mileage", "30.0"))
    max_cap = float(data_store.get_setting("max_mileage_cap", "50.0"))
    marathon_date_str = data_store.get_setting("marathon_date", "2026-11-01")

    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    total_weeks_remaining = max(1, (m_date - datetime.now().date()).days // 7)
    target_week_index = total_weeks_remaining - weeks_ahead

    if target_week_index <= 1:
        return round(max_cap * 0.40, 1)
    elif target_week_index == 2:
        return round(max_cap * 0.60, 1)
    elif target_week_index == 3:
        return round(max_cap * 0.75, 1)

    df = data_store.get_logs_df()
    current_vol = baseline
    if not df.empty:
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        weekly_totals = df.groupby('Week')['distance_miles'].sum()
        if not weekly_totals.empty: current_vol = max(weekly_totals.tail(3).max(), baseline)

    simulated_vol = current_vol
    for w in range(weeks_ahead + 1):
        if (w + 1) % 4 == 0:
            simulated_vol *= 0.85
        else:
            simulated_vol = min(simulated_vol * 1.08, max_cap)

    return round(min(simulated_vol, max_cap), 1)


def get_zero_filled_df():
    df = data_store.get_logs_df()
    if df.empty: return df
    df['log_date'] = pd.to_datetime(df['log_date'])
    full_idx = pd.date_range(start=df['log_date'].min(),
                             end=max(df['log_date'].max(), pd.to_datetime(datetime.now().date())), freq='D')
    df = df.set_index('log_date').reindex(full_idx)
    df.index.name = 'log_date'
    df['distance_miles'] = df['distance_miles'].fillna(0.0)
    df['cross_train_mins'] = df['cross_train_mins'].fillna(0)
    df['effective_miles'] = df['distance_miles'] + (df['cross_train_mins'] / 10.0)
    df['notes'] = df['notes'].fillna("")
    df['leg_soreness'] = df['leg_soreness'].fillna(1)
    return df.reset_index()


def calculate_target_paces(target_time_str: str) -> dict:
    try:
        parts = list(map(int, target_time_str.split(":")))
        total_mins = parts[0] * 60 + parts[1] + (parts[2] / 60.0 if len(parts) == 3 else 0)
    except Exception:
        total_mins = 210.0
    mp_sec = (total_mins * 60) / 26.2
    fmt = lambda s: f"{divmod(int(s), 60)[0]}:{divmod(int(s), 60)[1]:02d}/mi"
    return {
        "Goal Marathon Pace (MP)": fmt(mp_sec),
        "Easy / Recovery Pace": f"{fmt(mp_sec + 65)} - {fmt(mp_sec + 90)}",
        "Tempo / Threshold Pace": f"{fmt(mp_sec - 25)} - {fmt(mp_sec - 15)}",
        "Interval / VO2 Max Pace": f"{fmt(mp_sec - 50)} - {fmt(mp_sec - 40)}"
    }