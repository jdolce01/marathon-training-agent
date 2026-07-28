from datetime import datetime, date
import data_store

# Conversion ratio: 10 mins Zone 2 bike = 1.0 mile running equivalent
CROSS_TRAIN_MINS_PER_MILE = 10.0

def calculate_effective_miles(run_miles: float, cross_train_mins: int) -> float:
    """Calculates total aerobic volume including cross-training equivalency."""
    xt_miles = cross_train_mins / CROSS_TRAIN_MINS_PER_MILE
    return round(run_miles + xt_miles, 1)

def calculate_weeks_remaining() -> int:
    marathon_date_str = data_store.get_setting("marathon_date")
    if not marathon_date_str:
        return 16
    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    today = date.today()
    days_left = (m_date - today).days
    return max(1, days_left // 7)

def get_suggested_weekly_mileage() -> float:
    """
    Advanced Periodization Progression (e.g., Pfitzinger 18/70 curve):
    Peaks around 68-70 miles/week for experienced collegiate distance athletes.
    """
    weeks_out = calculate_weeks_remaining()
    
    # Advanced 18-Week Progression Schema
    schedule = {
        18: 48.0, 17: 52.0, 16: 56.0, 15: 60.0,
        14: 63.0, 13: 50.0, # Recovery week
        12: 65.0, 11: 68.0, 10: 70.0,  9: 55.0, # Recovery week
         8: 70.0,  7: 68.0,  6: 65.0,  5: 58.0,
         4: 62.0,  3: 50.0,  2: 38.0,  1: 22.0  # Taper phase
    }
    return schedule.get(weeks_out, 50.0)

def analyze_recent_trends_and_suggest():
    df = data_store.get_logs_df()
    if df.empty:
        return "No recent runs logged. Ready to launch your marathon block!"
    
    recent_3 = df.tail(3)
    avg_soreness = recent_3['leg_soreness'].mean()
    avg_feel = recent_3['overall_feel'].mean()
    
    advice = []
    
    if avg_soreness >= 3.8:
        suggested_bike_mins = 45
        equiv_miles = round(suggested_bike_mins / CROSS_TRAIN_MINS_PER_MILE, 1)
        advice.append(
            f"🚴 **Elevated Leg Fatigue Detected:** Your average leg soreness over the last 3 days is {avg_soreness:.1f}/5. "
            f"Swap today's run for **{suggested_bike_mins} minutes on the bike** in Zone 2. "
            f"This gives you **{equiv_miles} miles of running equivalent** while letting your legs recover."
        )
    elif avg_feel <= 2.0:
        advice.append(
            "⚠️ **Systemic Fatigue Warning:** Low overall feel ratings indicate compounding fatigue or high environmental stress. "
            "Consider reducing today's workout target volume by 20% and staying well-hydrated."
        )
    else:
        advice.append("🟢 **Green Light:** Legs and energy metrics are solid. Stick to your structured workout program!")
        
    return "\n\n".join(advice)
