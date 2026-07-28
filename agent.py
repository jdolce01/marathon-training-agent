from datetime import datetime, date
import data_store
import tools

CROSS_TRAIN_MINS_PER_MILE = 10.0

def calculate_effective_miles(run_miles: float, cross_train_mins: int) -> float:
    return round(run_miles + (cross_train_mins / CROSS_TRAIN_MINS_PER_MILE), 1)

def calculate_weeks_remaining() -> int:
    marathon_date_str = data_store.get_setting("marathon_date", "2026-11-01")
    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    days_left = (m_date - date.today()).days
    return max(1, days_left // 7)

def get_coaching_recommendation():
    """Generates an integrated coaching plan combining weather, soreness, and pain tools."""
    df = data_store.get_logs_df()
    
    advice = []
    
    # 1. Weather Alert
    weather_info = tools.get_weather_alert()
    advice.append(weather_info)
    
    if df.empty:
        advice.append("🟢 **Welcome to your build!** Enter your historical baseline in the settings tab to calculate your starting weekly target.")
        return "\n\n".join(advice)
        
    recent = df.tail(3)
    avg_soreness = recent['leg_soreness'].mean()
    
    # 2. Soreness Check
    if avg_soreness >= 3.8:
        advice.append("🚴 **High Fatigue Detected:** Leg soreness has averaged >= 4/5 over recent runs. Swap today's run for **45 mins on the stationary bike** (4.5 mi equivalent) to promote recovery.")
    else:
        advice.append("🟢 **Green Light:** Legs are adapting well. Proceed with planned training volume.")
        
    # 3. Check for recent Pain / Prehab needs
    latest_entry = df.iloc[-1]
    pain = latest_entry.get('pain_locations')
    if pain and pain != "None":
        exercises = tools.get_prehab_exercises(pain)
        ex_list = "\n".join([f"- {e}" for e in exercises])
        advice.append(f"🩹 **Prehab Recommendations for ({pain}):**\n{ex_list}")
        
    return "\n\n".join(advice)
