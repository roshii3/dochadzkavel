import streamlit as st
import pandas as pd
from datetime import datetime, time
from supabase import create_client, Client

# =====================================
# Konfigurácia aplikácie
# =====================================
st.set_page_config(page_title="Denný prehľad SBS", layout="wide")

# Skrytie hlavičky, menu a päty Streamlitu
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---------- CONFIG ----------
DATABAZA_URL = st.secrets["DATABAZA_URL"]
DATABAZA_KEY = st.secrets["DATABAZA_KEY"]
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "")  # nastav v secrets
databaze: Client = create_client(DATABAZA_URL, DATABAZA_KEY)

# Pozície v dochádzke
POSITIONS = [
    "Veliteľ", "CCTV", "Brány",
    "Sklad2", "Sklad3", "Turniket2",
    "Turniket3", "Plombovac2", "Plombovac3"
]

# Definícia časových rozsahov
RANNA_START, RANNA_END = time(3, 0), time(14, 0)
POOBEDNA_START, POOBEDNA_END = time(14, 0), time(23, 59)


# =====================================
# Funkcie
# =====================================
def get_today_data():
    today = datetime.now().date()
    tomorrow = today.replace(day=today.day + 1)
    resp = supabase.table("dochadzka")\
        .select("*")\
        .gte("timestamp", str(today))\
        .lt("timestamp", str(tomorrow))\
        .execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return pd.DataFrame(columns=["user_code", "action", "timestamp", "position", "valid"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def analyze_shift(df, position, start, end):
    """Vyhodnotí zmenu pre danú pozíciu"""
    df_pos = df[df["position"] == position]
    prichody = df_pos[df_pos["action"] == "Príchod"]["timestamp"].sort_values()
    odchody = df_pos[df_pos["action"] == "Odchod"]["timestamp"].sort_values()

    # Filtrovanie podľa časového intervalu
    prichody = prichody[(prichody.dt.time >= start) & (prichody.dt.time <= end)]
    odchody = odchody[(odchody.dt.time >= start) & (odchody.dt.time <= end)]

    if len(prichody) == 0:
        return "❌ bez príchodu"
    if len(odchody) == 0:
        return f"⚠ {prichody.iloc[0].time()} - zabudnutý odchod"
    return f"✅ {prichody.iloc[0].time()} - {odchody.iloc[-1].time()}"


def summarize_day(df, date):
    results = []
    for pos in POSITIONS:
        ranna = analyze_shift(df, pos, RANNA_START, RANNA_END)
        poobedna = analyze_shift(df, pos, POOBEDNA_START, POOBEDNA_END)
        results.append({"position": pos, "ranna": ranna, "poobedna": poobedna})
    return pd.DataFrame(results)


# =====================================
# UI – Denný prehľad
# =====================================
today = datetime.now().strftime("%A %d.%m.%Y")
st.title(f"🟢 Denný prehľad – {today}")

df_today = get_today_data()
df_summary = summarize_day(df_today, datetime.now().date())

# Zobrazenie v 3x3 matici
cols = st.columns(3)
for idx, row in df_summary.iterrows():
    with cols[idx % 3]:
        st.subheader(row["position"])
        st.write(f"Ranná: {row['ranna']}")
        st.write(f"Poobedná: {row['poobedna']}")
        st.markdown("---")
