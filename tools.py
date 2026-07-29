import requests
import pandas as pd
import re
from datetime import datetime, timedelta
import data_store

# REPORTLAB IMPORTS (Pure Python PDF Engine)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

HADDONFIELD_LAT = 39.8912
HADDONFIELD_LON = -75.0377


# 1. AUTOMATIC REAL-TIME WEATHER FETCH (Haddonfield, NJ)
def fetch_haddonfield_weather(log_date_str: str) -> dict:
    try:
        log_dt = datetime.strptime(log_date_str, "%Y-%m-%d").date()
        today_dt = datetime.now().date()

        if log_dt <= today_dt:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={HADDONFIELD_LAT}&longitude={HADDONFIELD_LON}&daily=temperature_2m_max,relative_humidity_2m_mean&temperature_unit=fahrenheit&timezone=America/New_York&start_date={log_date_str}&end_date={log_date_str}"
        else:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={HADDONFIELD_LAT}&longitude={HADDONFIELD_LON}&daily=temperature_2m_max,relative_humidity_2m_mean&temperature_unit=fahrenheit&timezone=America/New_York"

        res = requests.get(url, timeout=4).json()
        daily = res.get("daily", {})
        temps = daily.get("temperature_2m_max", [72.0])
        hums = daily.get("relative_humidity_2m_mean", [55.0])

        return {
            "temp_f": round(temps[0]) if temps else 72,
            "humidity_pct": round(hums[0]) if hums else 55
        }
    except Exception:
        return {"temp_f": 70, "humidity_pct": 50}


# 2. PDF TRAINING PLAN GENERATOR (INTEGER DISTANCES & SHOE ALERTS)
def generate_pdf_training_plan(output_pdf_path: str = "Julia_Marathon_Training_Plan.pdf") -> str:
    marathon_date_str = data_store.get_setting("marathon_date", "2026-11-01")
    target_time_str = data_store.get_setting("target_time", "03:30:00")
    max_cap = int(round(float(data_store.get_setting("max_mileage_cap", "50.0"))))
    max_long_run_cap = int(round(float(data_store.get_setting("max_long_run", "20.0"))))
    framework = data_store.get_setting("training_framework", "Pfitzinger (Pfitz)")

    shoe_name = data_store.get_setting("active_shoe_name", "Nike Pegasus 40")
    shoe_initial = float(data_store.get_setting("shoe_initial_miles", "0.0"))
    shoe_limit = float(data_store.get_setting("shoe_max_limit", "350.0"))

    df = data_store.get_logs_df()
    current_logged_miles = df['distance_miles'].sum() if not df.empty and 'distance_miles' in df else 0.0
    cum_shoe_miles = shoe_initial + current_logged_miles
    shoe_alert_triggered = False

    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    today_dt = datetime.now().date()
    weeks_left = max(1, (m_date - today_dt).days // 7)
    paces = calculate_target_paces(target_time_str)

    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20,
                            bottomMargin=20)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18,
                                 textColor=colors.HexColor('#0284c7'), spaceAfter=4)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
                               textColor=colors.HexColor('#475569'), spaceAfter=12)
    cell_style = ParagraphStyle('Cell', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#1e293b'))
    cell_bold = ParagraphStyle('CellB', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#0f172a'))
    header_cell = ParagraphStyle('HCell', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)
    shoe_warn_style = ParagraphStyle('ShoeWarn', fontName='Helvetica-Bold', fontSize=8,
                                     textColor=colors.HexColor('#dc2626'))

    elements = []
    elements.append(Paragraph("🏃 Custom Marathon Training Schedule", title_style))
    elements.append(
        Paragraph(f"Prepared for Julia Dolce | Location: Haddonfield, NJ | Target Race Date: {marathon_date_str}",
                  sub_style))

    meta_data = [
        [
            Paragraph("<b>Framework:</b> " + framework, cell_style),
            Paragraph("<b>Max Cap:</b> " + str(max_cap) + " mi/wk", cell_style),
            Paragraph("<b>Max Long Run:</b> " + str(max_long_run_cap) + " mi", cell_style),
            Paragraph("<b>Goal MP:</b> " + paces['Goal Marathon Pace (MP)'], cell_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[140, 120, 140, 140])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    table_data = [[
        Paragraph("Wk", header_cell),
        Paragraph("Dates", header_cell),
        Paragraph("Phase", header_cell),
        Paragraph("Target", header_cell),
        Paragraph("Mid-Week Run", header_cell),
        Paragraph("Long Run", header_cell),
        Paragraph("Gear & Shoe Alert", header_cell)
    ]]

    for w in range(1, weeks_left + 1):
        wk_target = int(round(calculate_periodized_target(weeks_ahead=w - 1)))
        wk_start = today_dt + timedelta(weeks=w - 1)
        wk_end = wk_start + timedelta(days=6)
        date_str = f"{wk_start.strftime('%b %d')} - {wk_end.strftime('%b %d')}"

        rev_index = weeks_left - w + 1
        if rev_index == 1:
            phase_tag = "Race Week"
            long_run = int(round(min(max_long_run_cap * 0.40, 8)))
        elif rev_index == 2:
            phase_tag = "Taper Wk 2"
            long_run = int(round(min(max_long_run_cap * 0.60, 12)))
        elif rev_index == 3:
            phase_tag = "Taper Wk 1"
            long_run = int(round(min(max_long_run_cap * 0.75, 15)))
        elif w % 4 == 0:
            phase_tag = "Cutback Wk"
            long_run = int(round(max_long_run_cap * 0.65))
        else:
            phase_tag = f"Build Step {(w % 4)}"
            pct_build = min(1.0, (w / (weeks_left - 3)))
            long_run = int(round(min(max_long_run_cap, max(10, max_long_run_cap * pct_build))))

        mid_long = int(round(min(wk_target * 0.22, 12)))

        cum_shoe_miles += wk_target
        shoe_note = Paragraph("OK", cell_style)
        if cum_shoe_miles >= shoe_limit and not shoe_alert_triggered:
            shoe_note = Paragraph(f"🚨 <b>Replace Shoes</b> ({int(round(cum_shoe_miles))} mi)", shoe_warn_style)
            shoe_alert_triggered = True

        table_data.append([
            Paragraph(f"Wk {w}", cell_style),
            Paragraph(date_str, cell_style),
            Paragraph(phase_tag, cell_bold),
            Paragraph(f"{wk_target} mi", cell_bold),
            Paragraph(f"{mid_long} mi Aerobic", cell_style),
            Paragraph(f"<b>{long_run} mi</b>", cell_style),
            shoe_note
        ])

    plan_table = Table(table_data, colWidths=[35, 90, 70, 55, 90, 80, 130])
    plan_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284c7')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(plan_table)
    doc.build(elements)
    return output_pdf_path


# 3. WORKOUT GENERATOR WITH INTEGER DISTANCES
def get_framework_workouts(weekly_target: float, framework: str, elevation: str) -> list:
    hill_note = " (Include 150-200ft elevation gain for hilly course prep)" if "Hilly" in elevation else ""
    max_long_run_cap = int(round(float(data_store.get_setting("max_long_run", "20.0"))))

    long_run = int(round(min(weekly_target * 0.38, max_long_run_cap)))

    if framework == "Pfitzinger (Pfitz)":
        mid_long = int(round(min(weekly_target * 0.22, 12)))
        tempo = int(round(max(3, weekly_target * 0.12)))
        return [
            {"name": "Pfitz Mid-Week Medium-Long Run", "type": "Aerobic Build",
             "desc": f"{mid_long} miles @ Easy/Aerobic pace.{hill_note}"},
            {"name": "Pfitz Lactate Threshold Run", "type": "Threshold",
             "desc": f"2 mi warmup + {tempo} mi @ LT Pace + 1 mi cooldown."},
            {"name": "Pfitz Long Run", "type": "Long Run",
             "desc": f"{long_run} miles steady effort, building to marathon pace in final 4 mi (Capped at {max_long_run_cap} mi).{hill_note}"}
        ]
    elif framework == "Hanson Method":
        hanson_cap = min(16, max_long_run_cap)
        long_run = int(round(min(weekly_target * 0.30, hanson_cap)))
        mp_run = int(round(min(weekly_target * 0.20, 10)))
        return [
            {"name": "Hanson Marathon Pace Run", "type": "Quality",
             "desc": f"2 mi warmup + {mp_run} mi @ Goal MP + 1 mi cooldown."},
            {"name": "Hanson Strength Intervals", "type": "Threshold",
             "desc": "3 x 2 miles @ 10s faster than MP with 800m recovery jog."},
            {"name": "Hanson Cumulative Fatigue Long Run", "type": "Long Run",
             "desc": f"{long_run} miles max on tired legs.{hill_note}"}
        ]
    else:  # Jack Daniels
        tempo = int(round(max(3, weekly_target * 0.10)))
        return [
            {"name": "Daniels Threshold Cruise Intervals", "type": "Threshold",
             "desc": f"4 x 1 mile @ Threshold Pace with 1 min rest."},
            {"name": "Daniels VO2 Max Intervals", "type": "Speed",
             "desc": "5 x 1000m @ I-Pace with 3 min jog recovery."},
            {"name": "Daniels Quality Long Run (2Q)", "type": "Long Run",
             "desc": f"{long_run} miles total: Easy + Threshold + Easy.{hill_note}"}
        ]


# 4. FATIGUE DIAGNOSTICS & OTHER HELPER FUNCTIONS
def analyze_notes_for_fatigue(text: str) -> list:
    if not text: return []
    text_lower = text.lower()
    fatigue_keywords = ["fatigue", "sluggish", "tired", "exhausted", "heavy legs", "low energy", "dizzy", "brain fog",
                        "drained", "poor sleep"]
    return list(set([kw for kw in fatigue_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)]))


def get_fatigue_health_diagnostics() -> str:
    return (
        "⚡ **Fatigue & Health Cause Diagnostics:**\n"
        "- **1. Carbohydrate / Glycogen Depletion:** Low glycogen stores make easy paces feel heavy. Target 3-5g carbs per kg bodyweight.\n"
        "- **2. Chronic Sleep Deficit:** Inadequate deep sleep impairs growth hormone release and muscle repair.\n"
        "- **3. Dehydration / Electrolyte Loss:** Deficits in sodium/potassium reduce blood plasma volume, raising heart rate.\n"
        "- **4. High Systemic / Neural Fatigue:** Accumulated training load without adequate cutback weeks.\n"
        "- **5. Low Ferritin / Iron Levels:** Common in high-mileage runners; reduces oxygen-carrying capacity."
    )


def calculate_hr_zones(max_hr: int, resting_hr: int) -> dict:
    hrr = max_hr - resting_hr
    return {
        "Zone 1 (Active Recovery)": f"{round(resting_hr + hrr * 0.50)} - {round(resting_hr + hrr * 0.60)} bpm",
        "Zone 2 (Aerobic / Easy Run)": f"{round(resting_hr + hrr * 0.60)} - {round(resting_hr + hrr * 0.70)} bpm",
        "Zone 3 (Marathon Pace)": f"{round(resting_hr + hrr * 0.70)} - {round(resting_hr + hrr * 0.80)} bpm",
        "Zone 4 (Threshold / Tempo)": f"{round(resting_hr + hrr * 0.80)} - {round(resting_hr + hrr * 0.90)} bpm",
        "Zone 5 (VO2 Max / Intervals)": f"{round(resting_hr + hrr * 0.90)} - {max_hr} bpm"
    }


def get_detailed_weather_forecast(latitude: float = HADDONFIELD_LAT, longitude: float = HADDONFIELD_LON) -> dict:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=precipitation_probability,temperature_2m,relative_humidity_2m&temperature_unit=fahrenheit&timezone=America/New_York"
    try:
        res = requests.get(url, timeout=5).json()
        hourly = res.get("hourly", {})
        times = hourly.get("time", [])
        precip = hourly.get("precipitation_probability", [])
        temps = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])

        tomorrow_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        morning_slots = []
        for t, p, temp, hum in zip(times, precip, temps, humidity):
            if t.startswith(tomorrow_date_str):
                hour = int(t.split("T")[1].split(":")[0])
                if 6 <= hour <= 9:
                    morning_slots.append({"time": f"{hour}:00 AM", "temp": round(temp), "humidity": hum, "precip": p})

        return {"date_str": (datetime.now() + timedelta(days=1)).strftime("%A, %b %d"), "slots": morning_slots}
    except Exception:
        return {"date_str": "Tomorrow", "slots": []}


def analyze_notes_for_pain(text: str) -> list:
    if not text: return []
    text_lower = text.lower()
    keywords = ["knee", "patellar", "it band", "shin", "achilles", "hip", "quad", "hamstring"]
    return [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)]


def get_prehab_for_keywords(keywords: list) -> dict:
    exercises = {
        "knee": ["Spanish Squats (4x45s holds)", "Single-Leg Step-Downs (3x10)", "VMO Quad Sets"],
        "patellar": ["Single-leg decline squats (3x10)", "Foam roll quads and IT band"],
        "it band": ["Clamshells with band (3x15)", "Standing IT Band Stretch", "Lateral Band Walks"],
        "shin": ["Tibialis Wall Raises (3x20)", "Eccentric Heel Drops (3x15)", "Towel Curls"],
        "achilles": ["Soleus Calf Stretch", "Eccentric Calf Drops (3x15)", "Golf Ball Foot Arch Roll"],
        "hip": ["Glute Bridges with 5s hold (3x12)", "90/90 Hip Flow", "Monster Walks"]
    }
    return {kw.title(): exercises.get(kw, ["10 mins general foam rolling and dynamic stretching"]) for kw in keywords}


def calculate_periodized_target(weeks_ahead: int = 0) -> float:
    baseline = float(data_store.get_setting("baseline_mileage", "30.0"))
    max_cap = float(data_store.get_setting("max_mileage_cap", "50.0"))
    marathon_date_str = data_store.get_setting("marathon_date", "2026-11-01")

    m_date = datetime.strptime(marathon_date_str, "%Y-%m-%d").date()
    total_weeks_remaining = max(1, (m_date - datetime.now().date()).days // 7)
    target_week_index = total_weeks_remaining - weeks_ahead

    if target_week_index <= 1:
        return int(round(max_cap * 0.40))
    elif target_week_index == 2:
        return int(round(max_cap * 0.60))
    elif target_week_index == 3:
        return int(round(max_cap * 0.75))

    df = data_store.get_logs_df()
    current_vol = baseline
    if not df.empty:
        df['Week'] = df['log_date'].dt.to_period('W').dt.start_time
        weekly_totals = df.groupby('Week')['distance_miles'].sum()
        if not weekly_totals.empty: current_vol = max(weekly_totals.tail(3).max(), baseline)

    simulated_vol = current_vol
    for w in range(weeks_ahead + 1):
        if (w + 1) % 4 == 0:
            simulated_vol *= 0.85
        else:
            simulated_vol = min(simulated_vol * 1.08, max_cap)

    return int(round(min(simulated_vol, max_cap)))


def get_zero_filled_df():
    df = data_store.get_logs_df()
    if df.empty:
        return df

    df['log_date'] = pd.to_datetime(df['log_date'])
    # Drop duplicate dates if any exist in raw logs
    df = df.drop_duplicates(subset=['log_date'])

    start_date = df['log_date'].min()
    end_date = max(df['log_date'].max(), pd.to_datetime(datetime.now().date()))

    full_idx = pd.date_range(start=start_date, end=end_date, freq='D')

    # Reindex cleanly without index collision
    df_indexed = df.set_index('log_date').reindex(full_idx)
    df_indexed.index.name = 'log_date'

    df_result = df_indexed.reset_index()
    df_result['distance_miles'] = df_result['distance_miles'].fillna(0.0)
    df_result['cross_train_mins'] = df_result['cross_train_mins'].fillna(0)
    df_result['effective_miles'] = df_result['distance_miles'] + (df_result['cross_train_mins'] / 10.0)
    df_result['notes'] = df_result['notes'].fillna("")
    df_result['leg_soreness'] = df_result['leg_soreness'].fillna(1)

    return df_result


def calculate_target_paces(target_time_str: str) -> dict:
    try:
        parts = list(map(int, target_time_str.split(":")))
        total_mins = parts[0] * 60 + parts[1] + (parts[2] / 60.0 if len(parts) == 3 else 0)
    except Exception:
        total_mins = 210.0
    mp_sec = (total_mins * 60) / 26.2
    fmt = lambda s: f"{divmod(int(s), 60)[0]}:{divmod(int(s), 60)[1]:02d}/mi"
    return {
        "Goal Marathon Pace (MP)": fmt(mp_sec),
        "Easy / Recovery Pace": f"{fmt(mp_sec + 65)} - {fmt(mp_sec + 90)}",
        "Tempo / Threshold Pace": f"{fmt(mp_sec - 25)} - {fmt(mp_sec - 15)}",
        "Interval / VO2 Max Pace": f"{fmt(mp_sec - 50)} - {fmt(mp_sec - 40)}"
    }


def get_shoe_mileage_status() -> dict:
    shoe_name = data_store.get_setting("active_shoe_name", "Primary Trainers")
    initial_miles = float(data_store.get_setting("shoe_initial_miles", "0.0"))
    max_limit = float(data_store.get_setting("shoe_max_limit", "350.0"))

    df = data_store.get_logs_df()
    logged_miles = 0.0
    if not df.empty and 'distance_miles' in df:
        logged_miles = df['distance_miles'].sum()

    total_miles = round(initial_miles + logged_miles, 1)
    pct_used = min(100.0, round((total_miles / max_limit) * 100, 1))

    status_alert = None
    if total_miles >= max_limit:
        status_alert = f"🚨 **Shoe Replacement Alert ({shoe_name}):** You have logged **{total_miles} miles** on this pair (Max limit: {int(max_limit)} mi). Replace to avoid joint strain."
    elif total_miles >= max_limit * 0.85:
        status_alert = f"👟 **Shoe Wear Warning ({shoe_name}):** You are at **{total_miles} miles** ({pct_used}% of life)."

    return {"shoe_name": shoe_name, "total_miles": total_miles, "max_limit": max_limit, "pct_used": pct_used,
            "alert": status_alert}