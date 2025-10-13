# streamlit_velitel_full.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

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
    df["time"] = df["timestamp"].dt.time
    df = df.sort_values("timestamp")
    return df

# ---------- GENEROVANIE PÁROV ----------
def generate_pairs(pos_df):
    """
    Generuje zoznam príchod/odchod párov.
    Zachováva všetky záznamy, aj nesparované.
    """
    pos_df = pos_df.sort_values("timestamp")
    pairs = []
    buffer_prichod = []

    for _, row in pos_df.iterrows():
        action = row["action"].lower()
        ts = row["timestamp"]
        if action == "príchod":
            buffer_prichod.append(ts)
        elif action == "odchod":
            if buffer_prichod:
                pr = buffer_prichod.pop(0)
                pairs.append({"prichod": pr, "odchod": ts})
            else:
                pairs.append({"prichod": None, "odchod": ts})

    # zostali príchody bez odchodov
    for pr in buffer_prichod:
        pairs.append({"prichod": pr, "odchod": None})

    return pairs

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
            if pos_df.empty:
                st.write("— žiadne záznamy —")
                continue
            pairs = generate_pairs(pos_df)
            for pair in pairs:
                pr_text = pair["prichod"].strftime("%H:%M") if pair["prichod"] else "—"
                od_text = pair["odchod"].strftime("%H:%M") if pair["odchod"] else "—"
                st.write(f"➡️ Príchod: {pr_text} | Odchod: {od_text}")
