import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_daily_feedback(recent_logs, today_log):
    system_prompt = (
        "You are an expert marathon coach specializing in collegiate-level runners transitioning "
        "to the marathon distance. Analyze the runner's last few days alongside today's run. "
        "Provide 2-3 concise sentences evaluating recovery, impact of weather/humidity, and "
        "whether to modify tomorrow's planned workout (e.g., recommend a bike/cross-train day "
        "if leg soreness scale <= 2 for consecutive days)."
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
