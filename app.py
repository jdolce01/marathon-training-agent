import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_store
import agent
import tools

st.set_page_config(page_title="Marathon AI Coach", page_icon="🏃", layout="wide")
data_store.init_db()

# DYNAMIC TIME-OF-DAY GREETING
st.title(agent.get_time_of_day_greeting("Julia"))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Weekly Dashboard",
    "🤖 Coach Advice Bot",
    "📝 Log Workout",
    "📅 History & Edit",
    "⚙️ Logistics & Plan Setup"
])

# --- TAB 1: WEEKLY DASHBOARD ---
with tab1:
    st.subheader("Weekly Volume & Periodization")
    target_mileage = tools.calculate_periodized_target(weeks_ahead=0)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Target Volume (This Week)", f"{target_mileage} mi")
    with c2:
        st.metric("Weeks to Marathon", f"{agent.calculate_weeks_remaining()} Wks Out")
    with c3:
        st.number_input("Override Target (mi)", value=target_mileage, step=1.0)

    st.markdown("### Agent Coaching Guidance")
    st.info(agent.get_coaching_recommendation())

    # Hourly Weather Cards
    weather_data = tools.get_detailed_weather_forecast()
    if weather_data.get("slots"):
        st.markdown(f"#### 🌤️ Hourly Forecast: {weather_data['date_str']} (Morning)")
        w_cols = st.columns(len(weather_data["slots"]))
        for idx, slot in enumerate(weather_data["slots"]):
            with w_cols[idx]:
                st.metric(slot["time"], f"{slot['temp']}°F", f"{slot['precip']}% Rain | {slot['humidity']}% Hum")

    st.markdown("---")

    # Framework Workouts Display
    sel_framework = data_store.get_setting("training_framework", "Pfitzinger (Pfitz)")
    sel_elevation = data_store.get_setting("course_elevation", "Flat / Fast (e.g. Philadelphia)")
    st.subheader(f"Suggested Workouts ({sel_framework})")
    workouts = tools.get_framework_workouts(target_mileage, sel_framework, sel_elevation)
    w_cols = st.columns(len(workouts))
    for idx, w in enumerate(workouts):
        with w_cols[idx]:
            st.markdown(f"**{w['name']}** *({w['type']})*")
            st.caption(w['desc'])

    st.markdown("---")

    # Daily Zero-Filled Plot
    st.subheader("Daily Running Volume (Rest Days Drop to 0)")
    df_daily = tools.get_zero_filled_df()
    if not df_daily.empty:
        fig_daily = px.line(df_daily, x='log_date', y='distance_miles', markers=True, template="plotly_dark")
        fig_daily.update_traces(line=dict(width=3), marker=dict(size=7))
        st.plotly_chart(fig_daily, use_container_width=True)

    # Weekly Toggle Bar Chart
    st.subheader("Week-by-Week Volume Progression")
    if not df_daily.empty:
        mileage_type = st.radio("Select Metric:",
                                ["Actual Running Miles", "Effective Mileage (Includes Cross-Training)"],
                                horizontal=True)
        df_daily['Week'] = df_daily['log_date'].dt.to_period('W').dt.start_time
        weekly_df = df_daily.groupby('Week').agg({'distance_miles': 'sum', 'effective_miles': 'sum'}).reset_index()
        y_col = 'distance_miles' if mileage_type == "Actual Running Miles" else 'effective_miles'

        fig_weekly = px.bar(weekly_df, x='Week', y=y_col, title=f"Weekly Summary ({mileage_type})",
                            template="plotly_dark", text_auto='.1f')
        st.plotly_chart(fig_weekly, use_container_width=True)

# --- TAB 2: ADVICE BOT ---
with tab2:
    st.subheader("💬 Interactive Coach Advice Bot")
    user_q = st.text_input("Ask your coach:", value="What will my mileage be in 4 weeks?")
    if st.button("Ask Bot"):
        st.markdown(agent.answer_user_query(user_q))

# --- TAB 3: LOG WORKOUT ---
with tab3:
    st.subheader("Daily Workout Log & Physical Check-In")
    with st.form("log_form"):
        log_date = st.date_input("Date", value=date.today())
        col1, col2 = st.columns(2)
        with col1:
            distance = st.number_input("Run Miles", min_value=0.0, step=0.5)
            workout_type = st.selectbox("Type", ["Easy Run", "Tempo/Threshold", "Long Run", "Rest", "Intervals"])
            avg_pace_input = st.text_input("Average Pace (MM:SS/mi)", value="08:30")
            soreness = st.slider("Leg Soreness (1-5)", 1, 5, 2)
        with col2:
            xt_mins = st.number_input("Bike/Elliptical Mins", min_value=0, step=5)
            feel = st.slider("Overall Feel (1-5)", 1, 5, 4)

        notes = st.text_area("Notes & Physical Discomfort Details",
                             placeholder="Example: Left knee felt sharp on downhills.")

        if st.form_submit_button("Submit Workout Log"):
            data_store.save_daily_log(str(log_date), distance, workout_type, "Morning", 70.0, 50.0, soreness, feel,
                                      xt_mins, avg_pace_input, notes)
            st.success("Log saved! Prehab guidance updated.")

# --- TAB 4: HISTORY ---
with tab4:
    st.subheader("Edit Historical Logs")
    df = data_store.get_logs_df()
    if not df.empty: st.data_editor(df, num_rows="dynamic")

# --- TAB 5: LOGISTICS & PLAN SETUP WITH FRAMEWORK READ-MORE ACCORDIONS ---
with tab5:
    st.subheader("⚙️ Marathon Plan & Framework Setup")

    col_a, col_b = st.columns(2)
    with col_a:
        current_m_date = data_store.get_setting("marathon_date", "2026-11-01")
        new_m_date = st.date_input("Marathon Date", value=datetime.strptime(current_m_date, "%Y-%m-%d").date())

        baseline_input = st.number_input("Starting Baseline Volume (mi/week)",
                                         value=float(data_store.get_setting("baseline_mileage", "30.0")), step=2.0)
        max_cap_input = st.number_input("Max Weekly Mileage Cap (mi/week)",
                                        value=float(data_store.get_setting("max_mileage_cap", "50.0")), step=5.0)
        target_time_input = st.text_input("Target Marathon Time (HH:MM:SS)",
                                          value=data_store.get_setting("target_time", "03:30:00"))

    with col_b:
        framework_input = st.selectbox(
            "Training Framework Methodology",
            ["Pfitzinger (Pfitz)", "Jack Daniels (Formula)", "Hanson Method"],
            index=["Pfitzinger (Pfitz)", "Jack Daniels (Formula)", "Hanson Method"].index(
                data_store.get_setting("training_framework", "Pfitzinger (Pfitz)"))
        )

        # --- READ MORE EXPANDERS FOR FRAMEWORKS ---
        with st.expander("📖 Read More: Pfitzinger (Pfitz) Framework"):
            st.markdown("""
            **Core Philosophy:** Heavy focus on building high aerobic capacity and lactate threshold. Signature element is the **Mid-Week Medium-Long Run (11–15 miles)**.
            * **Structure:** 1 Tempo/Threshold Run, 1 Mid-Week Medium-Long Run, 1 Weekend Long Run (up to 20 mi), 2–3 Easy Runs.
            * **Best For:** Runners with a solid baseline who build volume well and want strong stamina for the final 6 miles of the race.
            * **Mileage Adaptation:** Scaled down to a "Pfitz-Lite" schedule fitting your configured 35–50 mi cap.
            """)

        with st.expander("📖 Read More: Jack Daniels (Formula) Framework"):
            st.markdown("""
            **Core Philosophy:** Scientific VDOT pacing zones (E, M, T, I, R paces). Highly structured workouts tailored specifically to lactate threshold and VO2 max adaptations.
            * **Structure:** 2 Quality Workout Days (Threshold Cruise Intervals or Marathon Pace Long Runs) + 4 Easy/Recovery Days.
            * **Best For:** Goal-oriented runners who love exact pacing targets, structured track/tempo sessions, and precision.
            * **Mileage Adaptation:** Workouts scale as exact percentages of your weekly target volume.
            """)

        with st.expander("📖 Read More: Hanson Marathon Method"):
            st.markdown("""
            **Core Philosophy:** Cumulative Fatigue & No 20-Milers. Believes 20-mile runs on moderate volume cause excessive muscle damage. **Caps long runs at 16 miles**.
            * **Structure:** 1 Speed/Strength Workout, 1 Marathon Pace Run, 1 Capped Long Run (16 mi max on tired legs), 3 Easy Days.
            * **Best For:** Runners prone to injury on 18–20+ mile runs or those who prefer spreading volume evenly across 5–6 days.
            * **Mileage Adaptation:** Perfect for lower/moderate volume caps (35–45 mpw).
            """)

        elevation_input = st.selectbox(
            "Course Elevation Profile",
            ["Flat / Fast (e.g. Philadelphia)", "Hilly / Rolling (e.g. Boston/NYC)"],
            index=0 if "Flat" in data_store.get_setting("course_elevation", "Flat") else 1
        )

        max_hr_input = st.number_input("Max Heart Rate (BPM)", value=int(data_store.get_setting("max_hr", "185")),
                                       step=1)
        resting_hr_input = st.number_input("Resting Heart Rate (BPM)",
                                           value=int(data_store.get_setting("resting_hr", "55")), step=1)

    if st.button("Save Logistics & Framework Settings"):
        data_store.set_setting("marathon_date", str(new_m_date))
        data_store.set_setting("baseline_mileage", str(baseline_input))
        data_store.set_setting("max_mileage_cap", str(max_cap_input))
        data_store.set_setting("target_time", target_time_input)
        data_store.set_setting("training_framework", framework_input)
        data_store.set_setting("course_elevation", elevation_input)
        data_store.set_setting("max_hr", str(max_hr_input))
        data_store.set_setting("resting_hr", str(resting_hr_input))
        st.success("Logistics updated! Pacing, heart rate zones, and framework workouts recalculated.")

    st.markdown("---")
    st.subheader("🎯 Target Paces & Heart Rate Zones")

    col_pz, col_hr = st.columns(2)
    with col_pz:
        st.markdown("#### Calculated Target Paces")
        pace_zones = tools.calculate_target_paces(target_time_input)
        for z, p in pace_zones.items(): st.write(f"**{z}:** `{p}`")

    with col_hr:
        st.markdown("#### Calculated Heart Rate Zones")
        hr_zones = tools.calculate_hr_zones(int(max_hr_input), int(resting_hr_input))
        for z, r in hr_zones.items(): st.write(f"**{z}:** `{r}`")