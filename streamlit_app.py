# streamlit_velitel_prehľad.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client
from pathlib import Path

# ========== ZÁKLADNÉ NASTAVENIE ==========
st.set_page_config(page_title="Prehľad dochádzky — Veliteľ", layout="wide")

hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ========== DATABÁZA ==========
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
VELITEL_PASS = st.secrets.get("VELITEL_PASS", "")

databaza: Client = create_client(DATABAZA_URL, DATABAZA_KEY)
tz = pytz.timezone("Europe/Bratislava")

# ========== AUTORIZÁCIA ==========
app_dir = Path.home() / ".velitel_app"
app_dir.mkdir(parents=True, exist_ok=True)
AUTH_FILE = app_dir / "velitel_auth.txt"

def uloz_autorizaciu():
    with open(AUTH_FILE, "w") as f:
        f.write("OK")

def je_autorizovany():
    return AUTH_FILE.exists()

def odhlas_sa():
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()
    st.session_state.velitel_logged = False
    st.experimental_rerun()

# Inicializácia stavu
if "velitel_logged" not in st.session_state:
    st.session_state.velitel_logged = je_autorizovany()

# Login logika
if not st.session_state.velitel_logged:
    st.title("🔐 Prihlásenie veliteľa")
    pw = st.text_input("Zadaj heslo", type="password")
    if st.button("Prihlásiť sa"):
        if VELITEL_PASS and pw == VELITEL_PASS:
            uloz_autorizaciu()
            st.session_state.velitel_logged = True
            st.success("✅ Prihlásenie úspešné")
            st.experimental_rerun()
        else:
            st.error("❌ Nesprávne heslo.")
    st.stop()

# ========== HLAVNÝ OBSAH ==========
st.title("📋 Prehľad dochádzky — Veliteľ")
if st.button("🚪 Odhlásiť sa"):
    odhlas_sa()

if st.button("🔄 Obnoviť dáta"):
    st.experimental_rerun()

# ========== FUNKCIE ==========
def nacitaj_data():
    dnes = datetime.now(tz).date()
    vcera = dnes - timedelta(days=1)
    start = tz.localize(datetime.combine(vcera, datetime.min.time()))
    end = tz.localize(datetime.combine(dnes + timedelta(days=1), datetime.min.time()))
    
    res = databaza.table("attendance").select("*")\
        .gte("timestamp", start.isoformat())\
        .lt("timestamp", end.isoformat())\
        .execute()

    df = pd.DataFrame(res.data)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_convert("Europe/Bratislava")
    df["date"] = df["timestamp"].dt.date
    df["time"] = df["timestamp"].dt.strftime("%H:%M:%S")

    df = df.sort_values(["date", "position", "timestamp"])
    return df

# ========== ZOBRAZENIE ==========
data = nacitaj_data()

if data.empty:
    st.warning("Žiadne dáta za dnešok a včerajšok.")
else:
    for day in sorted(data["date"].unique(), reverse=True):
        st.subheader(f"📅 {day.strftime('%A %d.%m.%Y')}")
        day_df = data[data["date"] == day]

        for pos in sorted(day_df["position"].unique()):
            pos_df = day_df[day_df["position"] == pos]
            st.markdown(f"### 🔹 {pos}")

            records = []
            for _, r in pos_df.iterrows():
                records.append({
                    "Čas": r["time"],
                    "Akcia": r["action"],
                })
            df_view = pd.DataFrame(records)
            st.dataframe(df_view, use_container_width=True)
