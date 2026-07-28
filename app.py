import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_store
import agent

# Page Config & Custom Styling
st.set_page_config(page_title="Marathon AI Coach", page_icon="🏃", layout="wide")

# Initialize DB on start
data_store.init_db()

st.title("🏃 Marathon AI Coach")

# --- SIDEBAR: Target & Settings ---
with st.sidebar:
    st.header("⚙️ Settings & Goal")
    current_m_date = data_store.get_setting("marathon_date", "2026-11-01")
    new_m_date = st.date_input("Marathon Date", value=datetime.strptime(current_m_date, "%Y-%m-%d").date())
    
    if st.button("Save Date"):
        data_store.set_setting("marathon_date", str(new_m_date))
        st.success("Updated race date!")
    
    weeks_left = agent.calculate_weeks_remaining()
    st.metric("Weeks Until Race", f"{weeks_left} Weeks Out")

# --- MAIN TAB NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["📊 Weekly Plan & Analytics", "📝 Daily Log Entry", "📅 History & Retroactive Edit"])

# TAB 1: WEEKLY PLAN & PLOT
with tab1:
    st.subheader("Weekly Mileage Strategy")
    suggested_vol = agent.get_suggested_weekly_mileage()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Algorithm Suggested Volume", f"{suggested_vol} mi")
    with col2:
        user_override = st.number_input("Set/Override Weekly Volume (mi)", value=float(suggested_vol), step=1.0)
    
    st.markdown("### Adaptive Feedback")
    st.info(agent.analyze_recent_trends_and_suggest())
    
    # Plotting Mileage History
    st.markdown("### Recent Mileage History")
    df = data_store.get_logs_df()
    if not df.empty:
        # Group by week
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        weekly_df = df.groupby('Week')['distance_miles'].sum().reset_index()
        
        fig = px.bar(weekly_df, x='Week', y='distance_miles', 
                     title="Weekly Mileage Trend",
                     labels={'distance_miles': 'Miles', 'Week': 'Week Starting'},
                     template="plotly_dark", color_discrete_sequence=['#FF4B4B'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No mileage history available yet.")

# TAB 2: DAILY CHECK-IN FORM
with tab2:
    st.subheader("Post-Run Check-In")
    with st.form("daily_run_form"):
        log_date = st.date_input("Run Date", value=date.today())
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            distance = st.number_input("Distance (miles)", min_value=0.0, step=0.5)
            workout_type = st.selectbox("Type", ["Easy Run", "Workout/Tempo", "Long Run", "Cross-Training (Bike)", "Rest"])
        with col_b:
            time_of_day = st.selectbox("Time of Day", ["Morning", "Midday", "Evening"])
            temp = st.number_input("Temp (°F)", value=70.0)
        with col_c:
            humidity = st.slider("Humidity (%)", 0, 100, 50)
            
        col_d, col_e = st.columns(2)
        with col_d:
            soreness = st.slider("Leg Soreness (1 = Fresh, 5 = Sore)", 1, 5, 2)
        with col_e:
            feel = st.slider("Overall Feel (1 = Terrible, 5 = Great)", 1, 5, 4)
            
        notes = st.text_area("Notes / Factors (e.g., sleep, shoes, route effort)")
        
        submitted = st.form_submit_button("Save Entry")
        if submitted:
            data_store.save_daily_log(str(log_date), distance, workout_type, time_of_day, temp, humidity, soreness, feel, notes)
            st.success("Run logged successfully!")

# TAB 3: RETROACTIVE EDIT / TABLE VIEW
with tab3:
    st.subheader("Log History & Retroactive Edits")
    df = data_store.get_logs_df()
    if not df.empty:
        st.write("You can edit past data directly in the table below:")
        edited_df = st.data_editor(df, num_rows="dynamic")
    else:
        st.write("No logs recorded yet.")
