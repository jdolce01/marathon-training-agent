from datetime import datetime, date
import data_store
import tools


def get_time_of_day_greeting(name: str = "Julia") -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return f"Good morning, {name} ☀️"
    elif 12 <= hour < 18:
        return f"Good afternoon, {name} 🌤️"
    else:
        return f"Good evening, {name} 🌙"


def calculate_effective_miles(run_miles: float, cross_train_mins: int) -> float:
    return round(run_miles + (cross_train_mins / 10.0), 1)


def calculate_weeks_remaining() -> int:
    marathon_date_str = data_store.get_setting("marathon_date", "2026-11-01")
    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    days_left = (m_date - date.today()).days
    return max(1, days_left // 7)


def get_coaching_recommendation():
    df = data_store.get_logs_df()
    advice = []

    # Weather Forecast
    weather_data = tools.get_detailed_weather_forecast()
    slots = weather_data.get("slots", [])
    if slots:
        avg_temp = round(sum(s['temp'] for s in slots) / len(slots))
        max_rain = max(s['precip'] for s in slots)
        avg_hum = round(sum(s['humidity'] for s in slots) / len(slots))

        weather_str = f"🌡️ **Morning Weather Forecast ({weather_data['date_str']} 6-9 AM):** {avg_temp}°F | {avg_hum}% Humidity | {max_rain}% Rain Chance."
        if max_rain > 40:
            weather_str += " ⚠️ Rain likely; plan for rain gear or an indoor session."
        advice.append(weather_str)

    if df.empty:
        advice.append(
            "🟢 **Welcome to your marathon build!** Set up your marathon target date and volume caps in the **Logistics Setup** tab.")
        return "\n\n".join(advice)

    recent_7 = df.tail(7)

    # Free-Text Notes NLP Pain Extraction
    all_notes = " ".join(recent_7['notes'].dropna().tolist())
    detected_pains = tools.analyze_notes_for_pain(all_notes)

    if detected_pains:
        pains_str = ", ".join([p.title() for p in detected_pains])
        advice.append(
            f"⚠️ **Injury / Discomfort Alert ({pains_str}):** Pain keywords detected in your recent log notes. Consider reducing impact volume.")
        prehab_dict = tools.get_prehab_for_keywords(detected_pains)
        for area, ex_list in prehab_dict.items():
            ex_formatted = "\n".join([f"  - {e}" for e in ex_list])
            advice.append(f"🩹 **Targeted Prehab for {area}:**\n{ex_formatted}")
    else:
        advice.append(
            "🟢 **Physical Status Clear:** No injury keywords detected in your recent notes. Proceed with your scheduled workouts.")

    return "\n\n".join(advice)


# CONVERSATIONAL ADVICE BOT ENGINE
def answer_user_query(query: str) -> str:
    query_lower = query.lower()

    # 1. Multi-Week Projections
    if "week" in query_lower and (
            "how many" in query_lower or "in" in query_lower or "target" in query_lower or "future" in query_lower):
        import re
        numbers = re.findall(r'\b\d+\b', query_lower)
        weeks_ahead = int(numbers[0]) if numbers else 4
        projected = tools.calculate_periodized_target(weeks_ahead=weeks_ahead)
        return (
            f"📈 **Multi-Week Mileage Projection:**\n\n"
            f"- **In {weeks_ahead} Weeks:** Your projected target volume is **{projected} miles/week**.\n"
            f"- **Periodization Logic:** Includes periodized 4-week build cycles, cutback recovery weeks (-15%), and your configured volume cap of **{data_store.get_setting('max_mileage_cap', '50.0')} mi**."
        )

    # 2. Recovery Protocols
    elif "recover" in query_lower or "sore" in query_lower or "stiff" in query_lower:
        return (
            "🧘 **Optimal Recovery Protocol:**\n\n"
            "1. **30-Min Post-Run Window:** Consume 3:1 or 4:1 carbs-to-protein ratio (e.g., chocolate milk or smoothie).\n"
            "2. **Hydration & Electrolytes:** 16-24 oz of fluid per pound of sweat lost during quality runs.\n"
            "3. **Active Recovery:** 20-30 mins light spinning on bike or easy walking to flush metabolic waste.\n"
            "4. **Mobility:** Foam roll quads, calves, and hamstrings for 10 mins. Avoid deep aggressive stretching on acute strains."
        )

    # 3. Pacing Questions
    elif "pace" in query_lower:
        target_time = data_store.get_setting("target_time", "03:30:00")
        paces = tools.calculate_target_paces(target_time)
        return (
            f"⏱️ **Pace Breakdown for Target Finish ({target_time}):**\n\n"
            f"- **Goal Marathon Pace:** `{paces['Goal Marathon Pace (MP)']}`\n"
            f"- **Easy / Recovery Pace:** `{paces['Easy / Recovery Pace']}`\n"
            f"- **Tempo / Threshold Pace:** `{paces['Tempo / Threshold Pace']}`\n"
            f"- **Interval Pace:** `{paces['Interval / VO2 Max Pace']}`"
        )

    # 4. Default Guidance
    else:
        curr_target = tools.calculate_periodized_target(weeks_ahead=0)
        return (
            f"🏃 **Current Training Context:**\n\n"
            f"- **This Week's Target:** **{curr_target} mi**\n"
            f"- **Timeline:** **{calculate_weeks_remaining()} weeks** until marathon date.\n"
            f"- Ask me specific questions like: *'What will my mileage be in 6 weeks?'*, *'How should I recover after a long run?'*, or *'What is my goal tempo pace?'*"
        )