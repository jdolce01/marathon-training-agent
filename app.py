import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_store
import agent
import tools

st.set_page_config(page_title="Marathon AI Coach", page_icon="🏃", layout="wide")
data_store.init_db()

st.title(agent.get_time_of_day_greeting("Julia"))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Weekly Dashboard",
    "🤖 Coach Advice Bot",
    "📝 Log Workout",
    "📅 History & Edit",
    "⚙️ Logistics & Plan Setup"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Weekly Volume & Periodization")
    target_mileage = tools.calculate_periodized_target(weeks_ahead=0)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Target Volume (This Week)", f"{target_mileage} mi")
    with c2:
        st.metric("Weeks to Marathon", f"{agent.calculate_weeks_remaining()} Wks Out")

    # Shoe Alert Banner
    shoe_status = tools.get_shoe_mileage_status()
    if shoe_status["alert"]:
        st.warning(shoe_status["alert"])

    st.markdown("### Agent Coaching Guidance")
    st.info(agent.get_coaching_recommendation())

    # Weather Forecast
    weather_data = tools.get_detailed_weather_forecast()
    if weather_data.get("slots"):
        st.markdown(f"#### 🌤️ Hourly Forecast: {weather_data['date_str']} (Haddonfield, NJ Morning)")
        w_cols = st.columns(len(weather_data["slots"]))
        for idx, slot in enumerate(weather_data["slots"]):
            with w_cols[idx]:
                st.metric(slot["time"], f"{slot['temp']}°F", f"{slot['precip']}% Rain | {slot['humidity']}% Hum")

    st.markdown("---")

    # Download PDF Training Plan Button
    st.subheader("📄 Download Full Marathon PDF Schedule")
    pdf_filename = tools.generate_pdf_training_plan()
    with open(pdf_filename, "rb") as pdf_file:
        st.download_button(
            label="📥 Download Complete Custom PDF Plan",
            data=pdf_file,
            file_name="Julia_Marathon_Training_Plan.pdf",
            mime="application/pdf"
        )

    st.markdown("---")

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

    st.subheader("Daily Running Volume (Rest Days Drop to 0)")
    df_daily = tools.get_zero_filled_df()
    if not df_daily.empty:
        fig_daily = px.line(df_daily, x='log_date', y='distance_miles', markers=True, template="plotly_dark")
        fig_daily.update_traces(line=dict(width=3), marker=dict(size=7))
        st.plotly_chart(fig_daily, use_container_width=True)

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
    st.write("Ask specific questions about dates, max mileage specs, fatigue health causes, recovery, or pacing.")
    user_q = st.text_input("Ask your coach:", value="How far should I run on October 12th?")
    if st.button("Ask Bot"):
        st.markdown(agent.answer_user_query(user_q))

# --- TAB 3: LOG WORKOUT ---
with tab3:
    st.subheader("Daily Workout Log & Physical Check-In")
    with st.form("log_form"):
        log_date = st.date_input("Date", value=date.today())

        # Auto fetch weather for Haddonfield, NJ on selected date
        weather_info = tools.fetch_haddonfield_weather(str(log_date))
        st.caption(
            f"🌤️ **Auto-Fetched Weather (Haddonfield, NJ):** {weather_info['temp_f']}°F | {weather_info['humidity_pct']}% Humidity")

        col1, col2 = st.columns(2)
        with col1:
            distance = st.number_input("Run Miles", min_value=0.0, step=0.5)
            workout_type = st.selectbox("Type", ["Easy Run", "Tempo/Threshold", "Long Run", "Rest", "Intervals"])
            avg_pace_input = st.text_input("Average Pace (MM:SS/mi)", value="08:30")
            soreness = st.slider("Leg Soreness (1-5)", 1, 5, 2)
        with col2:
            xt_mins = st.number_input("Bike/Elliptical Mins", min_value=0, step=5)
            feel = st.slider("Overall Feel (1-5)", 1, 5, 4)
            active_shoe = data_store.get_setting("active_shoe_name", "Nike Pegasus 40")
            st.text_input("Running Shoe Pair", value=active_shoe, disabled=True)

        notes = st.text_area("Notes & Physical Details",
                             placeholder="Example: Left knee felt sharp on downhills, or felt super sluggish on mile 3.")

        if st.form_submit_button("Submit Workout Log"):
            data_store.save_daily_log(
                str(log_date), distance, workout_type, "Morning",
                weather_info['temp_f'], weather_info['humidity_pct'],
                soreness, feel, xt_mins, avg_pace_input, notes, active_shoe
            )
            st.success("Log saved! Real-time Haddonfield weather auto-recorded.")

# --- TAB 4: HISTORY ---
with tab4:
    st.subheader("Edit Historical Logs")
    df = data_store.get_logs_df()
    if not df.empty: st.data_editor(df, num_rows="dynamic")

# --- TAB 5: LOGISTICS & PLAN SETUP ---
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

        with st.expander("📖 Read More: Pfitzinger (Pfitz) Framework"):
            st.markdown("""
            **Core Philosophy:** Heavy focus on building high aerobic capacity and lactate threshold. Signature element is the **Mid-Week Medium-Long Run (11–15 miles)**.
            * **Structure:** 1 Tempo/Threshold Run, 1 Mid-Week Medium-Long Run, 1 Weekend Long Run (up to 20 mi), 2–3 Easy Runs.
            """)

        with st.expander("📖 Read More: Jack Daniels (Formula) Framework"):
            st.markdown("""
            **Core Philosophy:** Scientific VDOT pacing zones (E, M, T, I, R paces).
            * **Structure:** 2 Quality Workout Days + 4 Easy/Recovery Days.
            """)

        with st.expander("📖 Read More: Hanson Marathon Method"):
            st.markdown("""
            **Core Philosophy:** Cumulative Fatigue & No 20-Milers. **Caps long runs at 16 miles**.
            * **Structure:** 1 Speed/Strength Workout, 1 Marathon Pace Run, 1 Capped Long Run (16 mi max), 3 Easy Days.
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

    st.markdown("---")
    st.subheader("👟 Running Shoe Gear Tracker")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        shoe_name_input = st.text_input("Active Shoe Model",
                                        value=data_store.get_setting("active_shoe_name", "Nike Pegasus 40"))
    with col_s2:
        shoe_initial_input = st.number_input("Starting Mileage on Shoe",
                                             value=float(data_store.get_setting("shoe_initial_miles", "0.0")),
                                             step=10.0)
    with col_s3:
        shoe_limit_input = st.number_input("Shoe Lifespan Limit (mi)",
                                           value=float(data_store.get_setting("shoe_max_limit", "350.0")), step=25.0)

    if st.button("Save Logistics & Shoe Settings"):
        data_store.set_setting("marathon_date", str(new_m_date))
        data_store.set_setting("baseline_mileage", str(baseline_input))
        data_store.set_setting("max_mileage_cap", str(max_cap_input))
        data_store.set_setting("target_time", target_time_input)
        data_store.set_setting("training_framework", framework_input)
        data_store.set_setting("course_elevation", elevation_input)
        data_store.set_setting("max_hr", str(max_hr_input))
        data_store.set_setting("resting_hr", str(resting_hr_input))
        data_store.set_setting("active_shoe_name", shoe_name_input)
        data_store.set_setting("shoe_initial_miles", str(shoe_initial_input))
        data_store.set_setting("shoe_max_limit", str(shoe_limit_input))
        st.success("Logistics saved! PDF schedule updated.")

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