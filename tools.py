import requests
import data_store

# 1. PREHAB & EXERCISE LOOKUP TOOL
PREHAB_EXERCISES = {
    "knee_patellar": [
        "Spanish Squats / Isometric Wall Sits (4x45s holds)",
        "Eccentric Single-Leg Step-Downs (3x10)",
        "VMO Quad Sets"
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


# 2. LIVE HOURLY WEATHER FORECAST ALERT TOOL
def get_weather_alert(latitude: float = 39.8912, longitude: float = -75.0377) -> str:
    """Fetches hourly weather and checks for morning rain (>40% chance)."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=precipitation_probability,temperature_2m&temperature_unit=fahrenheit"
    try:
        res = requests.get(url, timeout=5).json()
        hourly = res.get("hourly", {})
        precip = hourly.get("precipitation_probability", [])
        
        # Check morning run window (6 AM - 9 AM tomorrow)
        morning_rain = any(p > 40 for p in precip[6:10])
        if morning_rain:
            return "🌧️ **Weather Alert:** High rain risk (>40%) forecasted tomorrow morning (6–9 AM). Consider shifting your run time or moving workouts indoors."
        return "☀️ **Weather Clear:** Morning conditions look great for running!"
    except Exception:
        return "Weather forecast currently unavailable."


# 3. MILEAGE BASELINE & PROGRESSION SCALER
def calculate_progressive_build(past_weeks_avg: float = None) -> float:
    """
    Safely increases weekly mileage by 8-10% based on recent baseline.
    """
    df = data_store.get_logs_df()
    
    # Use saved baseline setting if DB is empty
    if past_weeks_avg is None:
        past_weeks_avg = float(data_store.get_setting("baseline_mileage", "35.0"))
        
    if not df.empty:
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        recent_weeks = df.groupby('Week')['distance_miles'].sum().tail(3)
        if not recent_weeks.empty:
            past_weeks_avg = recent_weeks.mean()
            
    # Apply 8% step-up progression
    suggested_target = round(past_weeks_avg * 1.08, 1)
    return max(suggested_target, 25.0)
