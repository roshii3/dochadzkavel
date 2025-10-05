import streamlit as st
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ==========================
# ZÁKLADNÉ NASTAVENIA
# ==========================
st.set_page_config(page_title="Prehľad dochádzky", page_icon="📋", layout="wide")

hide_menu = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .reportview-container .markdown-text-container {
        font-size: 1.1rem;
    }
    </style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

# ==========================
# PRIPOJENIE NA DATABÁZU
# ==========================
DATABAZA_URL = st.secrets.get("DATABAZA_URL")
DATABAZA_KEY = st.secrets.get("DATABAZA_KEY")
supabase: Client = create_client(DATABAZA_URL, DATABAZA_KEY)

# ==========================
# AUTOMATICKÉ OBNOVOVANIE
# ==========================
st_autorefresh(interval=30000, key="datarefresh")  # každých 30 sekúnd

# ==========================
# FUNKCIA NA NAČÍTANIE DÁT
# ==========================
def nacitaj_data():
    tz = pytz.timezone("Europe/Bratislava")
    dnes = datetime.now(tz).date()
    vcera = dnes - timedelta(days=1)

    # Stiahneme posledné 2 dni
    result = supabase.table("attendance").select("*").execute()
    df = pd.DataFrame(result.data)

    if df.empty:
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["local_date"] = df["timestamp"].dt.tz_convert("Europe/Bratislava").dt.date
    df["local_time"] = df["timestamp"].dt.tz_convert("Europe/Bratislava").dt.strftime("%H:%M:%S")

    df = df[df["local_date"].isin([dnes, vcera])]

    # Skryjeme user_code
    df = df[["local_date", "local_time", "position", "action", "valid"]]
    df.rename(columns={
        "local_date": "Dátum",
        "local_time": "Čas",
        "position": "Pozícia",
        "action": "Akcia",
        "valid": "Platný čas"
    }, inplace=True)

    df["Platný čas"] = df["Platný čas"].apply(lambda x: "✅ Áno" if x else "⚠️ Nie")

    return df.sort_values(by=["Dátum", "Čas"], ascending=[False, True])

# ==========================
# HLAVNÉ ZOBRAZENIE
# ==========================
st.title("📋 Prehľad dochádzky (Veliteľ)")

if st.button("🔄 Obnoviť dáta"):
    st.experimental_rerun()

data = nacitaj_data()

if data.empty:
    st.info("Žiadne záznamy za dnešok ani včerajšok.")
else:
    # Rozdelenie podľa dátumu
    for datum, skupina in data.groupby("Dátum"):
        st.subheader(f"📅 {datum.strftime('%d.%m.%Y')}")
        st.dataframe(skupina, use_container_width=True, hide_index=True)
