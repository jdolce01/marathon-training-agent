import streamlit as st
import datetime
import plotly.express as px
import pandas as pd
from data_store import load_logs, save_log_entry, load_profile, save_profile
from agent import generate_daily_feedback, recommend_weekly_mileage

st.set_page_config(page_title="Marathon AI Coach", layout="wide")
st.title("🏃‍♂️ Adaptive Marathon Training Agent")

# Sidebar Configuration
st.sidebar.header("Athlete Profile & Target")
profile = load_profile()
marathon_date = st.sidebar.date_input("Marathon Date", datetime.date.fromisoformat(profile["marathon_date"]))
target_peak = st.sidebar.number_input("Target Peak Volume (mi)", value=profile["target_peak_mileage"])

if st.sidebar.button("Update Profile"):
    save_profile({"marathon_date": str(marathon_date), "target_peak_mileage": target_peak})
    st.sidebar.success("Updated Profile!")

weeks_out = max(0, (marathon_date - datetime.date.today()).days // 7)
st.sidebar.metric("Weeks Remaining", f"{weeks_out} weeks")

# Tabs Layout
tab1, tab2, tab3 = st.tabs(["📋 Daily Check-In", "🗓️ Weekly Planner", "📊 Analytics & Log"])

# TAB 1: DAILY CHECK-IN
with tab1:
    st.subheader("Daily Run Log")
    with st.form("daily_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            log_date = st.date_input("Date", datetime.date.today())
            planned_m = st.number_input("Planned Miles", min_value=0.0, step=0.5, value=8.0)
            actual_m = st.number_input("Actual Miles", min_value=0.0, step=0.5, value=8.0)
        with col2:
            time_of_day = st.time_input("Time of Run", datetime.time(7, 0))
            temp_f = st.number_input("Temperature (°F)", value=75)
            humidity = st.number_input("Humidity (%)", value=70)
        with col3:
            legs_rating = st.slider("Legs Feeling (1 = Very Sore, 5 = Fresh)", 1, 5, 3)
            feeling_rating = st.slider("Overall Feeling (1 = Exhausted, 5 = Great)", 1, 5, 3)
            notes = st.text_area("Notes / Workout details")
            
        submitted = st.form_submit_button("Log Run & Analyze")
        
    if submitted:
        entry = {
            "date": str(log_date),
            "planned_miles": planned_m,
            "actual_miles": actual_m,
            "time_of_day": str(time_of_day),
            "temp_f": temp_f,
            "humidity_pct": humidity,
            "legs_rating": legs_rating,
            "overall_feeling": feeling_rating,
            "notes": notes
        }
        save_log_entry(entry)
        st.success("Run logged successfully!")
        
        # Get AI Feedback
        df_logs = load_logs()
        with st.spinner("Coach AI analyzing run dynamics..."):
            feedback = generate_daily_feedback(df_logs, entry)
            st.info(f"**Coach Feedback:**\n\n{feedback}")

# TAB 2: WEEKLY PLANNER
with tab2:
    st.subheader("Sunday Mileage Planner")
    df_logs = load_logs()
    recent_avg = df_logs["actual_miles"].tail(7).sum() if not df_logs.empty else 40.0
    
    if st.button("Get AI Mileage Recommendation"):
        with st.spinner("Evaluating periodization plan..."):
            recommendation = recommend_weekly_mileage(weeks_out, recent_avg)
            st.write(recommendation)

# TAB 3: ANALYTICS
with tab3:
    st.subheader("Training Volume & Leg Feeling Trends")
    df_logs = load_logs()
    if not df_logs.empty:
        df_logs["date"] = pd.to_datetime(df_logs["date"])
        df_logs = df_logs.sort_values("date")
        
        fig = px.bar(
            df_logs, x="date", y="actual_miles", 
            color="legs_rating", 
            color_continuous_scale="RdYlGn",
            labels={"actual_miles": "Miles", "legs_rating": "Leg Rating (1-5)"},
            title="Daily Volume & Leg Soreness (Green = Fresh, Red = Sore)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No logs saved yet. Add your first run in the Daily Check-In tab!")
