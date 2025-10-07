# streamlit_velitel.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

# ---------- CONFIG ----------
st.set_page_config(page_title="Veliteľ - Dochádzka", layout="wide")
tz = pytz.timezone("Europe/Bratislava")

# ---------- DB ----------
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
VELITEL_PASSWORD = st.secrets["velitel_password"]
databaza: Client = create_client(DATABAZA_URL, DATABAZA_KEY)

POSITIONS = [
    "Veliteľ","CCTV","Brány","Sklad2",
    "Turniket2","Plombovac2","Sklad3",
    "Turniket3","Plombovac3"
]

# ---------- PRIHLASENIE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    pw = st.text_input("Zadaj heslo veliteľa", type="password")
    if st.button("Prihlásiť"):
        if pw == VELITEL_PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Nesprávne heslo.")
    st.stop()

# ---------- NAČÍTANIE DÁT ----------
def load_attendance(days=2):
    today = datetime.now(tz).date()
    start_dt = datetime.combine(today - timedelta(days=1), datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    res = databaza.table("attendance").select("*")\
        .gte("timestamp", start_dt.isoformat())\
        .lte("timestamp", end_dt.isoformat()).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["position","action","timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].dt.tz_localize(tz, ambiguous='NaT', nonexistent='shift_forward')\
                     .dt.tz_convert(tz)
    df["local_date"] = df["timestamp"].dt.date
    return df

df = load_attendance()

# ---------- PREHĽAD ----------
st.title("🕒 Prehľad dochádzky - Veliteľ")
st.write("Zobrazenie príchodov a odchodov pre dnešok a včerajšok.")

today = datetime.now(tz).date()
yesterday = today - timedelta(days=1)

for day in [yesterday, today]:
    st.subheader(day.strftime("%A %d.%m.%Y"))
    for pos in POSITIONS:
        pos_df = df[(df["position"] == pos) & (df["local_date"] == day)]
        if pos_df.empty:
            st.markdown(f"**{pos}:** ⚠️ Žiadne dáta")
            continue

        # Príchody a odchody
        prichody = pos_df[pos_df["action"] == "Príchod"]["timestamp"].tolist()
        odchody = pos_df[pos_df["action"] == "Odchod"]["timestamp"].tolist()
        
        st.markdown(f"**{pos}:**")
        for i in range(max(len(prichody), len(odchody))):
            pr = prichody[i].strftime("%H:%M:%S") if i < len(prichody) else "NaT"
            od = odchody[i].strftime("%H:%M:%S") if i < len(odchody) else "NaT"
            status = "✅ OK" if pr != "NaT" and od != "NaT" else "⚠ chýba údaj"
            st.markdown(f"- {status} — Príchod: {pr}, Odchod: {od}")
