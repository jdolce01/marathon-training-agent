from datetime import datetime, date, timedelta
import data_store

def calculate_weeks_remaining() -> int:
    marathon_date_str = data_store.get_setting("marathon_date")
    if not marathon_date_str:
        return 16  # Default fallback block length
    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    today = date.today()
    days_left = (m_date - today).days
    return max(1, days_left // 7)

def get_suggested_weekly_mileage() -> float:
    """
    Calculates periodized weekly volume target for an experienced runner 
    based on standard marathon build/taper principles (e.g., Pfitzinger / Daniels).
    """
    weeks_out = calculate_weeks_remaining()
    
    # 16-week build curve peaking around 55-70 miles/week for ex-collegiate runners
    if weeks_out > 16:
        return 45.0
    elif weeks_out > 12:
        return 50.0 + (16 - weeks_out) * 2.5  # Build phase 1
    elif weeks_out > 4:
        # Peak phase with periodic step-down recovery weeks
        if weeks_out in [8, 5]:
            return 48.0  # Recovery week
        return 62.0
    elif weeks_out == 3:
        return 50.0  # Taper start
    elif weeks_out == 2:
        return 38.0  # Taper mid
    else:
        return 22.0  # Race week (excluding race itself)

def analyze_recent_trends_and_suggest():
    """
    Evaluates soreness & feel over the last 3–5 days to output daily adaptations 
    (e.g., recommending a bike session if leg soreness >= 4 for two consecutive days).
    """
    df = data_store.get_logs_df()
    if df.empty:
        return "No recent runs logged. Ready to start your training block!"
    
    recent_3 = df.tail(3)
    avg_soreness = recent_3['leg_soreness'].mean()
    avg_feel = recent_3['overall_feel'].mean()
    
    advice = []
    if avg_soreness >= 3.8:
        advice.append("⚠️ **High Fatigue Detected:** Your leg fatigue has been elevated over the last few days. Consider swapping today's planned run for a 45-min cross-training session (spinning/bike) or an easy Z1 recovery jog.")
    elif avg_feel <= 2.0:
        advice.append("💡 **Low Overall Feel:** Heat/humidity or life stress may be compounding. Prioritize sleep and hydration; scale back today's volume by 15-20%.")
    else:
        advice.append("🟢 **Green Light:** Legs and overall recovery look strong. Proceed with planned workouts!")
        
    return "\n\n".join(advice)
