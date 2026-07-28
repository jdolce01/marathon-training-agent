import sqlite3
import pandas as pd

DB_FILE = "marathon_training.db"

def init_db():
    """Initializes SQLite database tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
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
            notes TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_targets (
            week_start_date TEXT PRIMARY KEY,
            suggested_mileage REAL,
            target_mileage REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def set_setting(key: str, value: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_setting(key: str, default=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def save_daily_log(log_date: str, distance: float, workout_type: str, 
                   time_of_day: str, temp: float, humidity: float, 
                   leg_soreness: int, overall_feel: int, cross_train_mins: int, notes: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO daily_logs 
        (log_date, distance_miles, workout_type, time_of_day, temp_f, humidity_pct, 
         leg_soreness, overall_feel, cross_train_mins, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (log_date, distance, workout_type, time_of_day, temp, humidity, leg_soreness, overall_feel, cross_train_mins, notes))
    conn.commit()
    conn.close()

def get_logs_df() -> pd.DataFrame:
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM daily_logs ORDER BY log_date ASC", conn)
    conn.close()
    if not df.empty:
        df['log_date'] = pd.to_datetime(df['log_date'])
    return df
