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

POSITIONS = ["Veliteľ", "CCTV", "Brány", "Sklad2", "Sklad3",
             "Turniket2", "Turniket3", "Plombovac2", "Plombovac3"]

# ---------- OVERENIE PRIHLASENIA ----------
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

# ---------- FUNKCIE ----------
def load_attendance(start_dt, end_dt):
    res = databaze.table("attendance").select("*") \
        .gte("timestamp", start_dt.isoformat()) \
        .lt("timestamp", end_dt.isoformat()).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].apply(
        lambda x: tz.localize(x) if pd.notna(x) and x.tzinfo is None else x
    )
    df["date"] = df["timestamp"].dt.date
    return df


def get_first_last_per_position(df_day):
    results = []
    for pos in POSITIONS:
        pos_df = df_day[df_day["position"] == pos]
        if pos_df.empty:
            results.append((pos, None, None))
            continue

        prichod = pos_df[pos_df["action"] == "Príchod"]["timestamp"].min()
        odchod = pos_df[pos_df["action"] == "Odchod"]["timestamp"].max()

        results.append((pos, prichod, odchod))
    return results


# ---------- ZOBRAZENIE ----------
st.title("🕒 Dochádzka - Veliteľ")

today = datetime.now(tz).date()
yesterday = today - timedelta(days=1)
start_dt = tz.localize(datetime.combine(yesterday, datetime.min.time()))
end_dt = tz.localize(datetime.combine(today + timedelta(days=1), datetime.min.time()))
df = load_attendance(start_dt, end_dt)

if df.empty:
    st.warning("⚠️ Nie sú dostupné žiadne dáta pre dnešok ani včerajšok.")
else:
    for day in [yesterday, today]:
        st.subheader(day.strftime("%A %d.%m.%Y"))
        df_day = df[df["date"] == day]
        if df_day.empty:
            st.write("— žiadne záznamy —")
            continue

        data = get_first_last_per_position(df_day)
        for pos, prichod, odchod in data:
            pr = prichod.strftime("%H:%M") if pd.notna(prichod) else "—"
            od = odchod.strftime("%H:%M") if pd.notna(odchod) else "—"
            st.write(f"**{pos}** — Príchod: {pr} | Odchod: {od}")
