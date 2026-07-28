import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "marathon_training.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            log_date TEXT PRIMARY KEY,
            distance_miles REAL,
            workout_type TEXT,
            time_of_day TEXT,
            temp_f REAL,
            humidity_pct REAL,
            leg_soreness INTEGER,
            overall_feel INTEGER,
            cross_train_mins INTEGER,
            pain_locations TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_setting(key: str, value: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_setting(key: str, default=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def save_daily_log(log_date, distance, workout_type, time_of_day, temp, humidity, 
                   soreness, feel, cross_train_mins, pain_locations, notes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO daily_logs 
        (log_date, distance_miles, workout_type, time_of_day, temp_f, humidity_pct, 
         leg_soreness, overall_feel, cross_train_mins, pain_locations, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (log_date, distance, workout_type, time_of_day, temp, humidity, soreness, feel, cross_train_mins, pain_locations, notes))
    conn.commit()
    conn.close()

def get_logs_df() -> pd.DataFrame:
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM daily_logs ORDER BY log_date ASC", conn)
    conn.close()
    if not df.empty:
        df['log_date'] = pd.to_datetime(df['log_date'])
    return df
