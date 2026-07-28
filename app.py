import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import data_store
import agent
import tools

st.set_page_config(page_title="Marathon AI Coach", page_icon="🏃", layout="wide")
data_store.init_db()

st.title("🏃 Marathon AI Coach")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Target Event & Baseline")
    current_m_date = data_store.get_setting("marathon_date", "2026-11-01")
    new_m_date = st.date_input("Marathon Date", value=datetime.strptime(current_m_date, "%Y-%m-%d").date())
    
    baseline = st.number_input("Past 3-4 Wk Avg Mileage", value=float(data_store.get_setting("baseline_mileage", "35.0")), step=2.0)
    
    if st.button("Save Settings"):
        data_store.set_setting("marathon_date", str(new_m_date))
        data_store.set_setting("baseline_mileage", str(baseline))
        st.success("Settings saved!")
    
    st.metric("Timeline", f"{agent.calculate_weeks_remaining()} Weeks Out")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Weekly Plan & Agent Insights", "📝 Log Workout", "📅 History & Edit"])

with tab1:
    st.subheader("Smart Weekly Target")
    suggested_mileage = tools.calculate_progressive_build(baseline)
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Suggested Weekly Target (10% Step-Up)", f"{suggested_mileage} mi")
    with c2:
        st.number_input("Override Weekly Target (mi)", value=suggested_mileage, step=1.0)
        
    st.markdown("### Agent Coaching Guidance")
    st.info(agent.get_coaching_recommendation())
    
    # Weekly Chart
    df = data_store.get_logs_df()
    if not df.empty:
        df['effective_miles'] = df.apply(lambda r: agent.calculate_effective_miles(r['distance_miles'], r['cross_train_mins']), axis=1)
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        weekly_df = df.groupby('Week')['effective_miles'].sum().reset_index()
        
        fig = px.bar(weekly_df, x='Week', y='effective_miles', title="Weekly Volume (Run + Bike Equivalent)", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Daily Entry & Physical Check-In")
    with st.form("log_form"):
        log_date = st.date_input("Date", value=date.today())
        
        col1, col2 = st.columns(2)
        with col1:
            distance = st.number_input("Run Miles", min_value=0.0, step=0.5)
            workout_type = st.selectbox("Type", ["Easy Run", "Tempo/Threshold", "Long Run", "Rest"])
            soreness = st.slider("Leg Soreness (1-5)", 1, 5, 2)
        with col2:
            xt_mins = st.number_input("Bike Mins", min_value=0, step=5)
            feel = st.slider("Overall Feel (1-5)", 1, 5, 4)
            pain = st.selectbox("Specific Joint/Muscle Pain", ["None", "Knee Patellar", "IT Band", "Shin Splints", "Achilles Plantar"])
            
        notes = st.text_area("Notes")
        
        if st.form_submit_button("Submit Log"):
            data_store.save_daily_log(str(log_date), distance, workout_type, "Morning", 70.0, 50.0, soreness, feel, xt_mins, pain, notes)
            st.success("Workout logged successfully!")

with tab3:
    st.subheader("Edit Historical Logs")
    df = data_store.get_logs_df()
    if not df.empty:
        st.data_editor(df, num_rows="dynamic")
