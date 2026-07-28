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
    """Generates reactive coaching plan by analyzing the past 7 days of entries."""
    df = data_store.get_logs_df()
    advice = []

    # 1. Weather Alert
    weather_info = tools.get_weather_alert()
    advice.append(weather_info)

    if df.empty:
        advice.append(
            "🟢 **Welcome to your build!** Enter your historical baseline in the settings tab to start your 10% step-up target.")
        return "\n\n".join(advice)

    # Analyze recent 7 days
    recent_7 = df.tail(7)
    avg_soreness = recent_7['leg_soreness'].mean() if 'leg_soreness' in recent_7 else 1

    # Check for active pain in recent logs
    recent_pains = []
    if 'pain_locations' in recent_7:
        recent_pains = [p for p in recent_7['pain_locations'].dropna().unique() if p != "None"]

    # 2. Pain & Injury Protocol
    if recent_pains:
        pains_str = ", ".join(recent_pains)
        advice.append(
            f"⚠️ **Injury Warning ({pains_str}):** Active joint/muscle pain detected in your recent logs. Reduce impact volume by replacing your next quality run with cross-training.")
        for p in recent_pains:
            ex_list = "\n".join([f"  - {e}" for e in tools.get_prehab_exercises(p)])
            advice.append(f"🩹 **Targeted Prehab for {p}:**\n{ex_list}")

    # 3. Fatigue Check
    elif avg_soreness >= 3.8:
        advice.append(
            "🚴 **High Fatigue Detected:** Leg soreness has averaged >= 4/5 recently. Swap today's run for **45 mins on the stationary bike** to promote recovery.")
    else:
        advice.append("🟢 **Green Light:** Fatigue levels are manageable. Proceed with your planned volume build.")

    return "\n\n".join(advice)