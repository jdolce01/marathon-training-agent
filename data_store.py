import sqlite3
import pandas as pd

DB_NAME = "marathon_training.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT UNIQUE,
            distance_miles REAL,
            workout_type TEXT,
            time_of_day TEXT,
            temp_f REAL,
            humidity_pct REAL,
            leg_soreness INTEGER,
            overall_feel INTEGER,
            cross_train_mins INTEGER,
            avg_pace TEXT,
            notes TEXT,
            shoe_name TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_daily_log(log_date, distance, workout_type, time_of_day, temp_f, humidity, soreness, feel, xt_mins, avg_pace, notes, shoe_name="Default Shoes"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO daily_logs (log_date, distance_miles, workout_type, time_of_day, temp_f, humidity_pct, leg_soreness, overall_feel, cross_train_mins, avg_pace, notes, shoe_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET
            distance_miles=excluded.distance_miles,
            workout_type=excluded.workout_type,
            time_of_day=excluded.time_of_day,
            temp_f=excluded.temp_f,
            humidity_pct=excluded.humidity_pct,
            leg_soreness=excluded.leg_soreness,
            overall_feel=excluded.overall_feel,
            cross_train_mins=excluded.cross_train_mins,
            avg_pace=excluded.avg_pace,
            notes=excluded.notes,
            shoe_name=excluded.shoe_name
    ''', (log_date, distance, workout_type, time_of_day, temp_f, humidity, soreness, feel, xt_mins, avg_pace, notes, shoe_name))
    conn.commit()
    conn.close()

def get_logs_df():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM daily_logs ORDER BY log_date ASC", conn)
    conn.close()
    if not df.empty:
        df['log_date'] = pd.to_datetime(df['log_date'])
    return df

def get_setting(key, default=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO user_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    conn.commit()
    conn.close()