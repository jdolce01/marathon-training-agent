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
    """Generates reactive coaching plan analyzing past logs and notes."""
    df = data_store.get_logs_df()
    advice = []

    # 1. Weather Alert
    weather_info = tools.get_weather_alert()
    advice.append(weather_info)

    if df.empty:
        advice.append(
            "🟢 **Welcome to your build!** Enter your historical baseline in settings to start your 10% step-up target.")
        return "\n\n".join(advice)

    recent_7 = df.tail(7)
    avg_soreness = recent_7['leg_soreness'].mean() if 'leg_soreness' in recent_7 else 1

    # 2. Free-text Pain Scanning from Notes & Dropdown
    notes_text = " ".join(recent_7['notes'].dropna().tolist())
    detected_pains = tools.analyze_notes_for_pain(notes_text)

    if 'pain_locations' in recent_7:
        for p in recent_7['pain_locations'].dropna().unique():
            if p and p != "None":
                detected_pains.append(p.lower())
    detected_pains = list(set(detected_pains))

    # 3. Pain & Prehab Guidance
    if detected_pains:
        pains_str = ", ".join([p.title() for p in detected_pains])
        advice.append(
            f"⚠️ **Injury Warning ({pains_str}):** Discomfort or pain detected in your recent logs/notes. Consider replacing your next high-impact run with cross-training.")
        prehab_dict = tools.get_prehab_for_keywords(detected_pains)
        for area, ex_list in prehab_dict.items():
            ex_formatted = "\n".join([f"  - {e}" for e in ex_list])
            advice.append(f"🩹 **Targeted Prehab for {area}:**\n{ex_formatted}")

    # 4. Fatigue Check
    elif avg_soreness >= 3.8:
        advice.append(
            "🚴 **High Fatigue Detected:** Average soreness is >= 4/5 recently. Swap today's run for **45 mins on the bike** to promote recovery.")
    else:
        advice.append("🟢 **Green Light:** Fatigue levels are manageable. Proceed with your planned training volume.")

    return "\n\n".join(advice)


# 5. INTERACTIVE ADVICE BOT ENGINE
def answer_user_query(query: str) -> str:
    """Answers user queries on pacing, daily distribution, and volume alignment."""
    df = tools.get_zero_filled_df()
    target_weekly = tools.calculate_progressive_build()

    # Analyze current week progress
    if not df.empty:
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        current_week_df = df[df['Week'] == df['Week'].max()]
        logged_miles = current_week_df['distance_miles'].sum()
        remaining_weekly_miles = max(0.0, target_weekly - logged_miles)
    else:
        logged_miles = 0.0
        remaining_weekly_miles = target_weekly

    query_lower = query.lower()
    target_pace_str = data_store.get_setting("target_time", "3:30:00")
    paces = tools.calculate_target_paces(target_pace_str)

    if "tomorrow" in query_lower or "pace" in query_lower or "distance" in query_lower:
        easy_pace = paces["Easy / Recovery Pace"]
        suggested_tomorrow = round(min(remaining_weekly_miles / 4.0, 8.0), 1) if remaining_weekly_miles > 0 else 4.0

        return (
            f"💡 **Custom Workout Recommendation for Tomorrow:**\n\n"
            f"- **Suggested Distance:** **{suggested_tomorrow} miles**\n"
            f"- **Target Pace Range:** **{easy_pace}** (Easy / Aerobic Build)\n"
            f"- **Weekly Mileage Context:** You have logged **{logged_miles:.1f} mi** out of your **{target_weekly} mi** target this week (**{remaining_weekly_miles:.1f} mi remaining**).\n\n"
            f"*Tip: Keep tomorrow's effort relaxed to save energy for your upcoming quality workout or long run!*"
        )
    else:
        return (
            f"🤖 **Coach Answer:** Based on your target weekly build of **{target_weekly} mi** (Goal Marathon Pace: **{paces['Goal Marathon Pace (MP)']}**), "
            f"focus on keeping 80% of your total weekly volume at **{paces['Easy / Recovery Pace']}**. "
            f"You currently have **{remaining_weekly_miles:.1f} miles** left to complete your weekly target."
        )