import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_store
import agent

st.set_page_config(page_title="Marathon AI Coach", page_icon="🏃", layout="wide")
data_store.init_db()

st.title("🏃 Advanced Marathon Coach & Mileage Engine")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Target Event")
    current_m_date = data_store.get_setting("marathon_date", "2026-11-01")
    new_m_date = st.date_input("Marathon Date", value=datetime.strptime(current_m_date, "%Y-%m-%d").date())
    
    if st.button("Update Race Date"):
        data_store.set_setting("marathon_date", str(new_m_date))
        st.success("Target date updated!")
    
    weeks_left = agent.calculate_weeks_remaining()
    st.metric("Timeline Status", f"{weeks_left} Weeks Out")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Weekly Plan & Analytics", "📝 Log Daily Workout", "📅 Calendar & Data Editor"])

# TAB 1: WEEKLY OVERVIEW & PLOT
with tab1:
    st.subheader("Weekly Mileage Periodization")
    suggested_vol = agent.get_suggested_weekly_mileage()
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Algorithm Target Volume", f"{suggested_vol} mi")
    with c2:
        user_override = st.number_input("Custom Target Volume (Override)", value=float(suggested_vol), step=1.0)
    
    st.markdown("### Adaptive Coaching Prompt")
    st.info(agent.analyze_recent_trends_and_suggest())
    
    st.markdown("### Recent Aerobic Volume Trend")
    df = data_store.get_logs_df()
    if not df.empty:
        # Calculate effective mileage
        df['effective_miles'] = df.apply(
            lambda r: agent.calculate_effective_miles(r['distance_miles'], r['cross_train_mins']), axis=1
        )
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        
        weekly_df = df.groupby('Week')['effective_miles'].sum().reset_index()
        
        fig = px.bar(
            weekly_df, x='Week', y='effective_miles',
            title="Weekly Total Volume (Run + Cross-Training Equivalent)",
            labels={'effective_miles': 'Total Miles (Equiv)', 'Week': 'Week Starting'},
            template="plotly_dark", color_discrete_sequence=['#3b82f6']
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No workouts logged yet. Start logging in the tab above!")

# TAB 2: DAILY LOGGING
with tab2:
    st.subheader("Daily Workout & Environmental Entry")
    with st.form("daily_run_form"):
        log_date = st.date_input("Date", value=date.today())
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            distance = st.number_input("Run Distance (miles)", min_value=0.0, step=0.5)
            workout_type = st.selectbox("Session Type", ["Easy Run", "Tempo/Threshold", "Intervals/Track", "Long Run", "Bike Cross-Training", "Rest"])
        with col_b:
            cross_train_mins = st.number_input("Cross-Training (Mins on Bike/Spin)", min_value=0, step=5)
            time_of_day = st.selectbox("Time of Day", ["Morning", "Midday", "Evening"])
        with col_c:
            temp = st.number_input("Temp (°F)", value=68.0)
            humidity = st.slider("Humidity (%)", 0, 100, 50)
            
        col_d, col_e = st.columns(2)
        with col_d:
            soreness = st.slider("Leg Soreness (1 = Fresh, 5 = Extremely Sore)", 1, 5, 2)
        with col_e:
            feel = st.slider("Overall Effort/Feel (1 = Terrible, 5 = Great)", 1, 5, 4)
            
        notes = st.text_area("Notes (Shoes, sleep, nutrition, HR stats, etc.)")
        
        if st.form_submit_button("Submit Workout Log"):
            data_store.save_daily_log(
                str(log_date), distance, workout_type, time_of_day, 
                temp, humidity, soreness, feel, cross_train_mins, notes
            )
            st.success("Run successfully recorded!")

# TAB 3: RETROACTIVE EDITING
with tab3:
    st.subheader("Interactive Historical Log")
    df = data_store.get_logs_df()
    if not df.empty:
        st.markdown("Double-click any cell to edit historical records retroactively:")
        edited_df = st.data_editor(df, num_rows="dynamic")
    else:
        st.write("No historical records available.")
