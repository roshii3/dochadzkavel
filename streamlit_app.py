# streamlit_velitel.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

# ---------- CONFIG ----------
st.set_page_config(page_title="Veliteľ - Dochádzka", layout="wide")
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ---------- DATABASE ----------
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
VELITEL_PASS = st.secrets["velitel_password"]
databaze: Client = create_client(DATABAZA_URL, DATABAZA_KEY)
tz = pytz.timezone("Europe/Bratislava")

POSITIONS = [
    "Veliteľ","CCTV","Brány","Sklad2",
    "Turniket2","Plombovac2","Sklad3",
    "Turniket3","Plombovac3"
]

# ---------- HELPERS ----------
def load_attendance(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    res = databaze.table("attendance").select("*")\
        .gte("timestamp", start_dt.isoformat())\
        .lt("timestamp", end_dt.isoformat()).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].apply(lambda x: tz.localize(x) if pd.notna(x) and x.tzinfo is None else x)
    df["local_date"] = df["timestamp"].dt.date
    return df

def summarize_day(df_day: pd.DataFrame):
    summary = {}
    for pos in POSITIONS:
        pos_df = df_day[df_day["position"] == pos].copy()
        if pos_df.empty:
            summary[pos] = []
            continue
        entries = []
        for idx, row in pos_df.iterrows():
            action = row["action"]
            timestamp = row["timestamp"]
            valid = row.get("valid", None)
            detail = f"{timestamp}" if pd.notna(timestamp) else "NaT"
            entries.append({"action": action, "detail": detail, "valid": valid})
        summary[pos] = entries
    return summary

# ---------- UI ----------
st.title("🕒 Prehľad dochádzky - Veliteľ")

# Heslo cez secret
if "velitel_logged" not in st.session_state:
    st.session_state.velitel_logged = False

if not st.session_state.velitel_logged:
    pw = st.text_input("Zadaj heslo", type="password")
    if st.button("Prihlásiť"):
        if pw == VELITEL_PASS:
            st.session_state.velitel_logged = True
            st.experimental_rerun()
        else:
            st.error("Nesprávne heslo!")
    st.stop()

# Dátumy: dnes a včerajšok
today = datetime.now(tz).date()
yesterday = today - timedelta(days=1)

start_dt = tz.localize(datetime.combine(yesterday, datetime.min.time()))
end_dt = tz.localize(datetime.combine(today + timedelta(days=1), datetime.min.time()))
df = load_attendance(start_dt, end_dt)

for day_label, day_date in [("Včerajšok", yesterday), ("Dnes", today)]:
    st.header(f"📅 {day_label} — {day_date.strftime('%A %d.%m.%Y')}")
    df_day = df[df["local_date"] == day_date]
    summary = summarize_day(df_day)
    for pos in POSITIONS:
        st.subheader(f"{pos}")
        entries = summary.get(pos, [])
        if not entries:
            st.write("— Žiadne záznamy —")
            continue
        for e in entries:
            status_icon = "✅" if e["valid"] else "⚠️" if e["valid"] is not None else "ℹ️"
            st.write(f"{status_icon} {e['action']} — {e['detail']}")
