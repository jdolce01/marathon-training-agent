import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import data_store
import agent
import tools

st.set_page_config(page_title="Marathon AI Coach", page_icon="🏃", layout="wide")
data_store.init_db()

st.title("🏃 Marathon AI Coach")

# --- SIDEBAR: SETTINGS & PACE ZONES ---
with st.sidebar:
    st.header("⚙️ Target Event & Goal Pace")

    current_m_date = data_store.get_setting("marathon_date", "2026-11-01")
    new_m_date = st.date_input("Marathon Date", value=datetime.strptime(current_m_date, "%Y-%m-%d").date())

    baseline = st.number_input("Past 3-4 Wk Avg Baseline (mi)",
                               value=float(data_store.get_setting("baseline_mileage", "35.0")), step=2.0)

    target_time_input = st.text_input("Target Marathon Time (HH:MM:SS)",
                                      value=data_store.get_setting("target_time", "03:30:00"))

    if st.button("Save Settings"):
        data_store.set_setting("marathon_date", str(new_m_date))
        data_store.set_setting("baseline_mileage", str(baseline))
        data_store.set_setting("target_time", target_time_input)
        st.success("Settings saved!")

    st.metric("Timeline", f"{agent.calculate_weeks_remaining()} Weeks Out")

    st.markdown("---")
    st.subheader("🎯 Calculated Pace Zones")
    pace_zones = tools.calculate_target_paces(target_time_input)
    for zone, p_range in pace_zones.items():
        st.write(f"**{zone}:** `{p_range}`")

# --- MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Weekly Plan & Insights",
    "🤖 Ask Advice Bot",
    "📝 Log Workout",
    "📅 History & Edit"
])

# --- TAB 1: DASHBOARD & CHARTS ---
with tab1:
    st.subheader("Weekly Target & Build")
    suggested_mileage = tools.calculate_progressive_build()

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Suggested Weekly Target (+10% Build)", f"{suggested_mileage} mi")
    with c2:
        st.number_input("Override Target (mi)", value=suggested_mileage, step=1.0)

    st.markdown("### Agent Coaching Guidance")
    st.info(agent.get_coaching_recommendation())

    st.markdown("---")
    st.subheader("Suggested Structured Workouts for This Week")
    workouts = tools.get_suggested_workouts(suggested_mileage)
    w_cols = st.columns(len(workouts))
    for idx, w in enumerate(workouts):
        with w_cols[idx]:
            st.markdown(f"**{w['name']}** *({w['type']})*")
            st.caption(w['desc'])

    st.markdown("---")

    # --- CHART 1: ZERO-FILLED DAILY DOT & RIGID LINE PLOT ---
    st.subheader("Daily Training Volume (Zero-Filled Rest Days)")
    df_daily = tools.get_zero_filled_df()
    if not df_daily.empty:
        fig_daily = px.line(
            df_daily,
            x='log_date',
            y='distance_miles',
            markers=True,
            title="Daily Running Mileage (Rest Days Drop to 0)",
            labels={'log_date': 'Date', 'distance_miles': 'Run Miles'},
            template="plotly_dark"
        )
        fig_daily.update_traces(line=dict(width=3), marker=dict(size=7))
        st.plotly_chart(fig_daily, use_container_width=True)

    # --- CHART 2: WEEK-BY-WEEK MILEAGE WITH TOGGLE ---
    st.subheader("Week-by-Week Mileage Build")
    if not df_daily.empty:
        mileage_type = st.radio("Select Mileage Metric:",
                                ["Actual Running Mileage", "Effective Mileage (Includes Cross-Training Conversion)"],
                                horizontal=True)

        df_daily['Week'] = df_daily['log_date'].dt.to_period('W').dt.start_time
        weekly_df = df_daily.groupby('Week').agg({
            'distance_miles': 'sum',
            'effective_miles': 'sum'
        }).reset_index()

        y_col = 'distance_miles' if mileage_type == "Actual Running Mileage" else 'effective_miles'

        fig_weekly = px.bar(
            weekly_df,
            x='Week',
            y=y_col,
            title=f"Weekly Total ({mileage_type})",
            labels={'Week': 'Week Starting', y_col: 'Total Miles'},
            template="plotly_dark",
            text_auto='.1f'
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

# --- TAB 2: INTERACTIVE ADVICE BOT ---
with tab2:
    st.subheader("💬 AI Marathon Advice Bot")
    st.write("Ask questions about your upcoming runs, daily distribution, pacing, or training plan adjustments.")

    user_q = st.text_input("Ask a question:",
                           value="What pace and distance should I run tomorrow so I am lined up well mileage wise for the rest of the week?")
    if st.button("Ask Bot"):
        response = agent.answer_user_query(user_q)
        st.markdown(response)

# --- TAB 3: WORKOUT LOGGING ---
with tab3:
    st.subheader("Daily Entry & Physical Check-In")
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
            pain = st.selectbox("Specific Joint/Muscle Pain (Optional Dropdown)",
                                ["None", "Knee", "IT Band", "Shin", "Achilles", "Hip"])

        notes = st.text_area("Notes & Discomfort Details (e.g. 'Left knee felt tight on downhill sections')")

        if st.form_submit_button("Submit Log"):
            data_store.save_daily_log(str(log_date), distance, workout_type, "Morning", 70.0, 50.0, soreness, feel,
                                      xt_mins, pain, avg_pace_input, notes)
            st.success("Workout logged successfully!")

# --- TAB 4: HISTORY ---
with tab4:
    st.subheader("Edit Historical Logs")
    df = data_store.get_logs_df()
    if not df.empty:
        st.data_editor(df, num_rows="dynamic")