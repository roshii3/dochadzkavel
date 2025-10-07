import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

# ---------- CONFIG ----------
st.set_page_config(page_title="Veliteľ - Dochádzka", layout="wide")
tz = pytz.timezone("Europe/Bratislava")

# Skrytie Streamlit menu
hide_menu = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

# ---------- AUTENTIFIKÁCIA ----------
def overenie_pristupu():
    st.title("🔐 Prihlásenie - Veliteľ")

    username_input = st.text_input("Používateľské meno:")
    password_input = st.text_input("Heslo:", type="password")

    velitel_username = st.secrets["VELITEL_USERNAME"]
    velitel_password = st.secrets["VELITEL_PASSWORD"]

    if st.button("Prihlásiť sa"):
        if username_input == velitel_username and password_input == velitel_password:
            st.session_state["velitel_prihlaseny"] = True
            st.success("✅ Úspešne prihlásený!")
            st.rerun()
        else:
            st.error("❌ Nesprávne meno alebo heslo")

if "velitel_prihlaseny" not in st.session_state:
    overenie_pristupu()
    st.stop()

# ---------- DATABASE ----------
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
databaza: Client = create_client(DATABAZA_URL, DATABAZA_KEY)

POSITIONS = [
    "Veliteľ", "CCTV", "Brány", "Sklad2",
    "Turniket2", "Plombovac2", "Sklad3",
    "Turniket3", "Plombovac3"
]

# ---------- FUNKCIE ----------
def load_attendance(days_back=1):
    """Načíta dochádzku za dnešok a včerajšok"""
    now = datetime.now(tz)
    start = now - timedelta(days=days_back)
    end = now + timedelta(days=1)

    res = databaza.table("attendance").select("*")\
        .gte("timestamp", start.isoformat())\
        .lt("timestamp", end.isoformat()).execute()
    
    df = pd.DataFrame(res.data)
    if df.empty:
        return df

    # Konverzia času
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if not df["timestamp"].isna().all():
        try:
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize(tz)
            else:
                df["timestamp"] = df["timestamp"].dt.tz_convert(tz)
        except Exception:
            df["timestamp"] = df["timestamp"].apply(
                lambda x: tz.localize(x) if (pd.notna(x) and x.tzinfo is None)
                else (x.tz_convert(tz) if pd.notna(x) else x)
            )
        df["local_date"] = df["timestamp"].dt.date
        df["local_time"] = df["timestamp"].dt.strftime("%H:%M:%S")
    return df

def summarize_day(df_day):
    """Vytvorí prehľad podľa pozícií"""
    summary = {}
    for pos in POSITIONS:
        pos_df = df_day[df_day["position"] == pos]
        if pos_df.empty:
            summary[pos] = []
            continue
        records = []
        for _, row in pos_df.iterrows():
            records.append({
                "action": row.get("action"),
                "time": row.get("local_time")
            })
        summary[pos] = records
    return summary

# ---------- UI ----------
st.title("🕒 Veliteľ - Denný prehľad dochádzky")

# Tlačidlo obnoviť
if st.button("🔄 Obnoviť"):
    st.session_state["refresh"] = datetime.now().timestamp()

if "refresh" not in st.session_state:
    st.session_state["refresh"] = None

df = load_attendance(days_back=1)

if df.empty:
    st.warning("⚠️ Žiadne záznamy za dnešok ani včerajšok.")
else:
    st.subheader("Prehľad za dnešok a včerajšok")
    summary = summarize_day(df)

    for pos in POSITIONS:
        st.markdown(f"### {pos}")
        records = summary.get(pos, [])
        if not records:
            st.info("Žiadne záznamy")
        else:
            for rec in records:
                time_str = rec["time"] or "NaT"
                action_emoji = "✅" if rec["action"] == "Príchod" else "🚪"
                st.write(f"{action_emoji} {rec['action']} — {time_str}")
