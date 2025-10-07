# streamlit_velitel.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

# ---------- CONFIG ----------
st.set_page_config(page_title="Veliteľ - Dochádzka", layout="wide")

# Skrytie menu a footeru
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ---------- DATABASE ----------
DATABAZA_URL = st.secrets.get("DATABAZA_URL")
DATABAZA_KEY = st.secrets.get("DATABAZA_KEY")
VELITEL_PASSWORD = st.secrets.get("velitel_password")
databaza: Client = create_client(DATABAZA_URL, DATABAZA_KEY)
tz = pytz.timezone("Europe/Bratislava")

POSITIONS = [
    "Veliteľ","CCTV","Brány","Sklad2",
    "Turniket2","Plombovac2","Sklad3",
    "Turniket3","Plombovac3"
]

# ---------- LOGIN ----------
if "velitel_logged" not in st.session_state:
    st.session_state.velitel_logged = False

def prihlasenie():
    if not st.session_state.velitel_logged:
        st.subheader("🔐 Prihlásenie veliteľa")
        password = st.text_input("Heslo", type="password")
        if st.button("Prihlásiť"):
            if password == VELITEL_PASSWORD:
                st.session_state.velitel_logged = True
                st.experimental_rerun()
            else:
                st.error("❌ Nesprávne heslo")

prihlasenie()
if not st.session_state.velitel_logged:
    st.stop()

# ---------- DATA ----------
def nacitaj_data():
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    start_dt = tz.localize(datetime.combine(yesterday, datetime.min.time()))
    end_dt = tz.localize(datetime.combine(today, datetime.max.time()))
    
    res = databaza.table("attendance").select("*")\
        .gte("timestamp", start_dt.isoformat())\
        .lte("timestamp", end_dt.isoformat())\
        .execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].apply(
        lambda x: tz.localize(x) if pd.notna(x) and x.tzinfo is None else (x.tz_convert(tz) if pd.notna(x) else x)
    )
    df["local_date"] = df["timestamp"].dt.date
    return df

# ---------- UI ----------
st.title("🕒 Veliteľ - Denný prehľad dochádzky")

if st.button("🔄 Obnoviť"):
    st.experimental_rerun()

data = nacitaj_data()
if data.empty:
    st.warning("⚠️ Nie sú dostupné žiadne údaje za dnešok ani včerajšok")
    st.stop()

for pos in POSITIONS:
    st.subheader(f"📌 {pos}")
    pos_df = data[data["position"] == pos].sort_values("timestamp")
    if pos_df.empty:
        st.write("— žiadne záznamy —")
        continue

    table = []
    for _, row in pos_df.iterrows():
        table.append({
            "Dátum": row["local_date"],
            "Akcia": row["action"],
            "Čas": row["timestamp"].strftime("%H:%M:%S"),
            "Status": "Platný" if row.get("valid", True) else "Mimo času"
        })
    df_table = pd.DataFrame(table)
    st.dataframe(df_table, use_container_width=True)
