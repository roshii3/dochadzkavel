import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client

# ==============================
# Streamlit konfigurácia
# ==============================
st.set_page_config(page_title="Denný prehľad – Veliteľ", page_icon="🕒", layout="wide")
st.markdown("<h2 style='text-align:center;'>🕒 Denný prehľad prítomnosti</h2>", unsafe_allow_html=True)

# Skrytie menu a footeru
hide_style = """
<style>
#MainMenu, footer, header {visibility: hidden;}
</style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# ==============================
# Automatický refresh
# ==============================
st_autorefresh = st.experimental_rerun
st_autorefresh_count = st.experimental_get_query_params().get("refresh", [0])[0]
st_autorefresh_count = int(st_autorefresh_count) + 1
st.markdown(f"<meta http-equiv='refresh' content='30;url=?refresh={st_autorefresh_count}'>", unsafe_allow_html=True)

# ==============================
# Pripojenie k databáze
# ==============================
DATABAZA_URL = st.secrets.get("DATABAZA_URL")
DATABAZA_KEY = st.secrets.get("DATABAZA_KEY")
supabase: Client = create_client(DATABAZA_URL, DATABAZA_KEY)

tz = pytz.timezone("Europe/Bratislava")
today = datetime.now(tz).date()
yesterday = today - timedelta(days=1)

# ==============================
# Načítanie dát
# ==============================
@st.cache_data(ttl=20)
def load_data():
    res = supabase.table("attendance").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    return df

df = load_data()

if df.empty:
    st.warning("⚠️ Žiadne dáta pre zobrazenie.")
    st.stop()

# ==============================
# Spracovanie dát
# ==============================
def summarize_day(df_day):
    records = []
    for pos, group in df_day.groupby("position"):
        arrivals = group[group["action"] == "Príchod"]
        departures = group[group["action"] == "Odchod"]

        pr_times = sorted(arrivals["timestamp"].dt.strftime("%H:%M").tolist())
        od_times = sorted(departures["timestamp"].dt.strftime("%H:%M").tolist())

        pr_display = ", ".join(pr_times) if pr_times else "—"
        od_display = ", ".join(od_times) if od_times else "—"

        if pr_times and od_times:
            status = "🟢 OK"
        elif pr_times or od_times:
            status = "🟠 Chýba údaj"
        else:
            status = "🔴 Bez záznamu"

        records.append({
            "Pozícia": pos,
            "Príchody": pr_display,
            "Odchody": od_display,
            "Stav": status
        })
    return pd.DataFrame(records)

# ==============================
# Zobrazenie
# ==============================
tab1, tab2 = st.tabs([f"Dnes ({today.strftime('%d.%m.%Y')})", f"Včera ({yesterday.strftime('%d.%m.%Y')})"])

with tab1:
    df_today = df[df["date"] == today]
    if df_today.empty:
        st.info("Žiadne záznamy pre dnešok.")
    else:
        summary_today = summarize_day(df_today)
        st.dataframe(summary_today, use_container_width=True, hide_index=True)

with tab2:
    df_yest = df[df["date"] == yesterday]
    if df_yest.empty:
        st.info("Žiadne záznamy pre včerajšok.")
    else:
        summary_yest = summarize_day(df_yest)
        st.dataframe(summary_yest, use_container_width=True, hide_index=True)

# ==============================
# Poznámka o automatickom obnovení
# ==============================
st.caption("⏳ Dáta sa automaticky obnovujú každých 30 sekúnd.")
