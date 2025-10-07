# streamlit_velitel.py
import streamlit as st
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client
import pandas as pd

st.set_page_config(page_title="Veliteľ - Dochádzka", layout="wide")

# Skryť menu a footer
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ---------------- CONFIG ----------------
DATABAZA_URL = st.secrets.get("DATABAZA_URL")
DATABAZA_KEY = st.secrets.get("DATABAZA_KEY")
VELITEL_PASSWORD = st.secrets.get("velitel_password")
databaza: Client = create_client(DATABAZA_URL, DATABAZA_KEY)

tz = pytz.timezone("Europe/Bratislava")
POSITIONS = ["Veliteľ","CCTV","Brány","Sklad2","Sklad3","Turniket2","Turniket3","Plombovac2","Plombovac3"]

# ---------------- Funkcie ----------------
def prihlasenie():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        pw = st.text_input("Heslo veliteľa", type="password")
        if st.button("Prihlásiť"):
            if pw == VELITEL_PASSWORD:
                st.session_state.logged_in = True
                st.experimental_rerun()
            else:
                st.error("Nesprávne heslo!")
        st.stop()

def nacitaj_data():
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    start_dt = datetime.combine(yesterday, datetime.min.time()).astimezone(tz)
    end_dt = datetime.combine(today, datetime.max.time()).astimezone(tz)

    res = databaza.table("attendance").select("*")\
        .gte("timestamp", start_dt.isoformat())\
        .lte("timestamp", end_dt.isoformat())\
        .execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["position","action","timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].apply(lambda x: x.tz_convert(tz) if pd.notna(x) and x.tzinfo else x)
    df["local_date"] = df["timestamp"].dt.date
    return df

def summary_table(df):
    data = []
    for pos in POSITIONS:
        pos_df = df[df["position"] == pos]
        for d in sorted(pos_df["local_date"].unique(), reverse=True):
            day_df = pos_df[pos_df["local_date"] == d]
            arrivals = day_df[day_df["action"]=="Príchod"]["timestamp"].dt.strftime("%H:%M:%S").tolist()
            departures = day_df[day_df["action"]=="Odchod"]["timestamp"].dt.strftime("%H:%M:%S").tolist()
            data.append({
                "Pozícia": pos,
                "Dátum": d,
                "Príchody": ", ".join(arrivals) if arrivals else "—",
                "Odchody": ", ".join(departures) if departures else "—"
            })
    return pd.DataFrame(data)

# ---------------- Hlavný blok ----------------
prihlasenie()
st.title("🕒 Dochádzka - Veliteľ")

df = nacitaj_data()
if df.empty:
    st.warning("⚠ Dáta nie sú dostupné pre dnešok ani včerajšok.")
else:
    st.subheader("📋 Prehľad príchodov a odchodov (dnešok + včerajšok)")
    df_table = summary_table(df)
    st.dataframe(df_table, use_container_width=True)
