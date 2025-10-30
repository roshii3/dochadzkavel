# streamlit_velitel_full.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import pytz
from supabase import create_client, Client

# ---------- CONFIG ----------
st.set_page_config(page_title="Veliteľ - Dochádzka", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ---------- DB ----------
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
VELITEL_PASS = st.secrets["velitel_password"]
databaze: Client = create_client(DATABAZA_URL, DATABAZA_KEY)
tz = pytz.timezone("Europe/Bratislava")

POSITIONS = ["Veliteľ","CCTV","Brány","Sklad2","Sklad3","Turniket2","Turniket3","Plombovac2","Plombovac3"]

# ---------- LOGIN ----------
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
    return df

# ---------- VYPIS VSETKYCH ZAZNAMOV ----------
def all_entries(pos_df: pd.DataFrame):
    """
    Vráti všetky príchody a odchody pre pozíciu, chronologicky.
    """
    if pos_df.empty:
        return []
    df_sorted = pos_df.sort_values("timestamp")
    entries = []
    for _, row in df_sorted.iterrows():
        ts_str = row["timestamp"].strftime("%H:%M") if pd.notna(row["timestamp"]) else "—"
        entries.append(f"➡️ {row['action']}: {ts_str}")
    return entries

# ---------- ZOBRAZENIE DÁT ----------
st.title("🕒 Prehľad dochádzky - Veliteľ")

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
        for pos in POSITIONS:
            st.markdown(f"**{pos}**")
            pos_df = df_day[df_day["position"] == pos]
            entries = all_entries(pos_df)
            if not entries:
                st.write("— žiadne záznamy —")
            else:
                for e in entries:
                    st.write(e)
# ---------- TABUĽKA ODCHODOV VELITEĽA ZA TENTO TÝŽDEŇ ----------
st.subheader("📋 Potvrdené odchody veliteľa (aktuálny týždeň)")

# Výpočet pondelka aktuálneho týždňa
today_dt = datetime.now(tz)
monday_dt = today_dt - timedelta(days=today_dt.weekday())
start_week = tz.localize(datetime.combine(monday_dt.date(), datetime.min.time()))
end_week = tz.localize(datetime.combine(today_dt.date() + timedelta(days=1), datetime.min.time()))

# Načítanie dát len pre tento týždeň
df_week = load_attendance(start_week, end_week)

if not df_week.empty:
    # Filtrovanie len pre pozíciu Veliteľ a akciu "odchod"
    df_velitel = df_week[(df_week["position"] == "Veliteľ") & (df_week["action"].str.lower() == "odchod")]
    if df_velitel.empty:
        st.info("Žiadne potvrdené odchody veliteľa v tomto týždni.")
    else:
        df_velitel["Dátum"] = df_velitel["timestamp"].dt.strftime("%d.%m.%Y")
        df_velitel["Čas"] = df_velitel["timestamp"].dt.strftime("%H:%M")
        df_tab = df_velitel[["Dátum", "Čas", "position", "action"]].rename(
            columns={"position": "Pozícia", "action": "Akcia"}
        ).sort_values(["Dátum", "Čas"])
        st.dataframe(df_tab, use_container_width=True)
else:
    st.info("Nie sú dostupné dáta pre tento týždeň.")
