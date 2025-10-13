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

# ---------- DB ----------
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
VELITEL_PASS = st.secrets["velitel_password"]
databaze: Client = create_client(DATABAZA_URL, DATABAZA_KEY)
tz = pytz.timezone("Europe/Bratislava")

POSITIONS = ["Veliteľ","CCTV","Brány","Sklad2","Sklad3","Turniket2","Turniket3","Plombovac2","Plombovac3"]

# ---------- PRIHLÁSENIE ----------
if "velitel_logged" not in st.session_state:
    st.session_state.velitel_logged = False

if not st.session_state.velitel_logged:
    password = st.text_input("Zadaj heslo pre prístup", type="password")
    if st.button("Prihlásiť"):
        if password == VELITEL_PASS:
            st.session_state.velitel_logged = True
        else:
            st.error("Nesprávne heslo.")
    st.stop()

# ---------- NAČÍTANIE DÁT ----------
def load_attendance(start_dt, end_dt):
    res = databaze.table("attendance").select("*")\
        .gte("timestamp", start_dt.isoformat())\
        .lt("timestamp", end_dt.isoformat()).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].apply(lambda x: tz.localize(x) if pd.notna(x) and x.tzinfo is None else x)
    df["date"] = df["timestamp"].dt.date
    df["time"] = df["timestamp"].dt.strftime("%H:%M")
    return df

# ---------- HLAVIČKA ----------
st.title("🕒 Prehľad dochádzky - Veliteľ")

today = datetime.now(tz).date()
yesterday = today - timedelta(days=1)
start_dt = tz.localize(datetime.combine(yesterday, datetime.min.time()))
end_dt = tz.localize(datetime.combine(today + timedelta(days=1), datetime.min.time()))
df = load_attendance(start_dt, end_dt)

# ---------- SPRACOVANIE ----------
if df.empty:
    st.warning("⚠️ Nie sú dostupné žiadne dáta pre dnešok ani včerajšok.")
else:
    records = []
    for (pos, date), group in df.groupby(["position", "date"]):
        group = group.sort_values("timestamp")
        prichod = None
        for _, row in group.iterrows():
            if row["action"] == "Príchod" and prichod is None:
                prichod = row["time"]
            elif row["action"] == "Odchod" and prichod is not None:
                records.append({
                    "date": date,
                    "position": pos,
                    "Príchod": prichod,
                    "Odchod": row["time"]
                })
                prichod = None
        if prichod is not None:
            records.append({
                "date": date,
                "position": pos,
                "Príchod": prichod,
                "Odchod": "—"
            })

    final_df = pd.DataFrame(records).sort_values(by=["date", "position", "Príchod"])

    # ---------- ZOBRAZENIE ----------
    for date, group in final_df.groupby("date"):
        st.subheader(date.strftime("%A %d.%m.%Y"))
        for pos, pos_group in group.groupby("position"):
            st.markdown(f"### {pos}")
            for _, row in pos_group.iterrows():
                st.write(f"➡️ Príchod: {row['Príchod']} | Odchod: {row['Odchod']}")
            st.markdown("<hr style='border:1px solid #ddd;'>", unsafe_allow_html=True)
