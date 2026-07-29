from datetime import datetime, date, timedelta
import re
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

    weather_data = tools.get_detailed_weather_forecast()
    slots = weather_data.get("slots", [])
    if slots:
        avg_temp = round(sum(s['temp'] for s in slots) / len(slots))
        max_rain = max(s['precip'] for s in slots)
        avg_hum = round(sum(s['humidity'] for s in slots) / len(slots))

        weather_str = f"🌡️ **Morning Weather Forecast (Haddonfield, NJ - 6-9 AM):** {avg_temp}°F | {avg_hum}% Humidity | {max_rain}% Rain Chance."
        if max_rain > 40:
            weather_str += " ⚠️ Rain likely; consider an indoor treadmill option."
        advice.append(weather_str)

    if df.empty:
        advice.append("🟢 **Welcome to your marathon build!** Set up your logistics parameters in the setup tab.")
        return "\n\n".join(advice)

    recent_7 = df.tail(7)

    # 1. Injury Note Extraction
    all_notes = " ".join(recent_7['notes'].dropna().tolist())
    detected_pains = tools.analyze_notes_for_pain(all_notes)

    if detected_pains:
        pains_str = ", ".join([p.title() for p in detected_pains])
        advice.append(
            f"⚠️ **Discomfort Alert ({pains_str}):** Discomfort keywords detected in your notes. Reduce impact volume.")
        prehab_dict = tools.get_prehab_for_keywords(detected_pains)
        for area, ex_list in prehab_dict.items():
            ex_formatted = "\n".join([f"  - {e}" for e in ex_list])
            advice.append(f"🩹 **Targeted Prehab for {area}:**\n{ex_formatted}")

    # 2. Fatigue Diagnostic Extraction
    fatigue_matches = tools.analyze_notes_for_fatigue(all_notes)
    if fatigue_matches:
        advice.append(tools.get_fatigue_health_diagnostics())

    if not detected_pains and not fatigue_matches:
        advice.append("🟢 **Status Clear:** No physical discomfort or high fatigue keywords detected in recent notes.")

    return "\n\n".join(advice)


# ENHANCED CONVERSATIONAL ADVICE BOT ENGINE
def answer_user_query(query: str) -> str:
    query_lower = query.lower()

    # 1. SPECIFIC DATE MILEAGE QUERY (e.g., "how far should I run on September 15th")
    date_match = re.search(
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\b',
        query_lower)
    if date_match or "date" in query_lower or "on" in query_lower:
        max_cap = float(data_store.get_setting("max_mileage_cap", "50.0"))
        framework = data_store.get_setting("training_framework", "Pfitzinger (Pfitz)")

        # Calculate target for that week
        target_wk = tools.calculate_periodized_target(weeks_ahead=2)
        if framework == "Hanson Method":
            long_run = round(min(target_wk * 0.30, 16.0), 1)
        else:
            long_run = round(min(target_wk * 0.35, 20.0), 1)

        easy_run = round(target_wk * 0.15, 1)

        return (
            f"📅 **Specific Date Guidance:**\n\n"
            f"- **Target Long Run for That Week:** **{long_run} miles** (Weekend)\n"
            f"- **Target Mid-Week Easy Run:** **{easy_run} miles**\n"
            f"- **Total Weekly Target:** **{target_wk} miles/week** (Max Cap: **{max_cap} mi** under **{framework}** framework)."
        )

    # 2. MAX MILEAGE SPECIFICATION QUERY
    elif "max" in query_lower or "cap" in query_lower or "limit" in query_lower:
        max_cap = data_store.get_setting("max_mileage_cap", "50.0")
        baseline = data_store.get_setting("baseline_mileage", "30.0")
        framework = data_store.get_setting("training_framework", "Pfitzinger (Pfitz)")
        return (
            f"⚙️ **Mileage Specifications & Limits:**\n\n"
            f"- **Max Weekly Mileage Cap:** **{max_cap} mi/week**\n"
            f"- **Starting Baseline:** **{baseline} mi/week**\n"
            f"- **Selected Framework:** **{framework}**\n"
            f"- **Periodization:** 3-week volume build (+8% to +10%) followed by a 1-week cutback (-15%) and a 3-week pre-race taper."
        )

    # 3. FATIGUE & HEALTH REASONS
    elif "fatigue" in query_lower or "sluggish" in query_lower or "tired" in query_lower or "health" in query_lower:
        return tools.get_fatigue_health_diagnostics()

    # 4. MULTI-WEEK PROJECTIONS
    elif "week" in query_lower and (
            "how many" in query_lower or "in" in query_lower or "target" in query_lower or "future" in query_lower):
        numbers = re.findall(r'\b\d+\b', query_lower)
        weeks_ahead = int(numbers[0]) if numbers else 4
        projected = tools.calculate_periodized_target(weeks_ahead=weeks_ahead)
        return (
            f"📈 **Multi-Week Mileage Projection:**\n\n"
            f"- **In {weeks_ahead} Weeks:** Your projected target volume is **{projected} miles/week**.\n"
            f"- Configured volume ceiling cap is **{data_store.get_setting('max_mileage_cap', '50.0')} mi**."
        )

    # 5. RECOVERY PROTOCOLS
    elif "recover" in query_lower or "sore" in query_lower or "stiff" in query_lower:
        return (
            "🧘 **Optimal Recovery Protocol:**\n\n"
            "1. **Post-Run Fueling:** Consuming 3:1 carbs-to-protein ratio within 30 minutes.\n"
            "2. **Hydration:** Rehydrate with 16-24 oz electrolytes per pound of sweat lost.\n"
            "3. **Active Recovery:** 20-30 mins light spinning on bike to promote circulation.\n"
            "4. **Sleep Hygiene:** Target 8+ hours to maximize growth hormone recovery."
        )

    # 6. PACING QUERY
    elif "pace" in query_lower:
        target_time = data_store.get_setting("target_time", "03:30:00")
        paces = tools.calculate_target_paces(target_time)
        return (
            f"⏱️ **Target Pace Breakdown ({target_time} Goal):**\n\n"
            f"- **Goal Marathon Pace:** `{paces['Goal Marathon Pace (MP)']}`\n"
            f"- **Easy / Recovery Pace:** `{paces['Easy / Recovery Pace']}`\n"
            f"- **Tempo Pace:** `{paces['Tempo / Threshold Pace']}`\n"
            f"- **Interval Pace:** `{paces['Interval / VO2 Max Pace']}`"
        )

    # 7. DEFAULT GUIDANCE
    else:
        curr_target = tools.calculate_periodized_target(weeks_ahead=0)
        return (
            f"🏃 **Current Training Context:**\n\n"
            f"- **This Week's Target:** **{curr_target} mi**\n"
            f"- **Timeline:** **{calculate_weeks_remaining()} weeks** out.\n"
            f"- Ask me specific questions like: *'How far should I run on October 12th?'*, *'What are my max mileage specs?'*, or *'Why am I feeling sluggish?'*"
        )