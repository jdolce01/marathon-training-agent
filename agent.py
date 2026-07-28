import os
import streamlit as st
from openai import OpenAI

def get_openai_client():
    # Check Streamlit Cloud Secrets first, then local environment variable
    api_key = None
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        st.error("⚠️ OpenAI API Key not found. Please add OPENAI_API_KEY to Streamlit Secrets or environment variables.")
        st.stop()
        
    return OpenAI(api_key=api_key)

def generate_daily_feedback(recent_logs, today_log):
    client = get_openai_client()
    system_prompt = (
        "You are an expert marathon coach specializing in collegiate-level runners transitioning "
        "to the marathon distance. Analyze the runner's last few days alongside today's run. "
        "Provide 2-3 concise sentences evaluating recovery, impact of weather/humidity, and "
        "whether to modify tomorrow's planned workout."
    )
    
    user_content = f"""
    Recent Logs (Last 5 days):
    {recent_logs.tail(5).to_dict(orient='records')}

    Today's Run Log:
    {today_log}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

def recommend_weekly_mileage(weeks_out, recent_weekly_avg):
    client = get_openai_client()
    system_prompt = (
        "You are an expert distance running coach. Suggest a weekly target mileage for a former "
        "collegiate runner building for a marathon. Follow standard periodization rules "
        "(max 10% volume increase per week, 3 weeks build + 1 drop-back week)."
    )
    user_content = f"Runner is {weeks_out} weeks out from the marathon. Recent weekly average is {recent_weekly_avg} miles."
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content
