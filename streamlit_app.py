import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from pytz import timezone

# =============================
# 🔐 PRIHLÁSENIE CEZ SECRETS
# =============================
def prihlasenie():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Prihlásenie - Veliteľ")

        password = st.text_input("Zadaj heslo:", type="password")

        if st.button("Prihlásiť"):
            if password == st.secrets["velitel_password"]:
                st.session_state["authenticated"] = True
                st.success("✅ Úspešne prihlásený!")
                st.rerun()
            else:
                st.error("❌ Nesprávne heslo.")
        st.stop()


# =============================
# 🔗 PRIPOJENIE K DATABÁZE
# =============================
def get_connection():
    conn = psycopg2.connect(
        host=st.secrets["connections"]["postgres"]["host"],
        dbname=st.secrets["connections"]["postgres"]["dbname"],
        user=st.secrets["connections"]["postgres"]["user"],
        password=st.secrets["connections"]["postgres"]["password"],
        port=st.secrets["connections"]["postgres"]["port"],
        sslmode="require"
    )
    return conn


# =============================
# 📥 NAČÍTANIE DÁT
# =============================
def nacitaj_data():
    conn = get_connection()
    query = """
        SELECT position_name, timestamp, event_type
        FROM dochadzka
        ORDER BY timestamp DESC;
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # časové pásmo
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["local_time"] = df["timestamp"].dt.tz_convert("Europe/Bratislava")
    df["local_date"] = df["local_time"].dt.date

    return df


# =============================
# 🧮 SPRACOVANIE PREHĽADU
# =============================
def priprav_prehľad(df):
    dnes = datetime.now(timezone("Europe/Bratislava")).date()
    vcera = dnes - timedelta(days=1)

    df = df[df["local_date"].isin([dnes, vcera])]

    prehlad = {}

    for pos, group in df.groupby("position_name"):
        zaznamy = group.sort_values("local_time")

        prichody = zaznamy[zaznamy["event_type"] == "prichod"]["local_time"].tolist()
        odchody = zaznamy[zaznamy["event_type"] == "odchod"]["local_time"].tolist()

        prehlad[pos] = {"prichody": prichody, "odchody": odchody}

    return prehlad, dnes, vcera


# =============================
# 🎨 ZOBRAZENIE PREHĽADU
# =============================
def zobraz_prehľad(prehlad, dnes, vcera):
    st.title("📋 Denný prehľad dochádzky")

    for pos, data in sorted(prehlad.items()):
        st.markdown(f"### 🏷️ {pos}")

        # prichody
        if len(data["prichody"]) == 0 and len(data["odchody"]) == 0:
            st.warning("Žiadne dáta za dnešok ani včerajšok.")
            continue

        # zobrazenie časov
        if len(data["prichody"]) > 0:
            st.write("**Príchody:**")
            for t in data["prichody"]:
                st.markdown(f"- 🟢 {t.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.markdown("- ⚠️ Žiadny príchod")

        if len(data["odchody"]) > 0:
            st.write("**Odchody:**")
            for t in data["odchody"]:
                st.markdown(f"- 🔴 {t.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.markdown("- ⚠️ Žiadny odchod")

        st.divider()


# =============================
# 🔄 HLAVNÁ APLIKÁCIA
# =============================
def main():
    prihlasenie()

    # Tlačidlo Obnoviť (bez chýb)
    if "refresh" not in st.session_state:
        st.session_state["refresh"] = 0

    if st.button("🔄 Obnoviť"):
        st.session_state["refresh"] += 1

    if st.session_state["refresh"] >= 0:
        df = nacitaj_data()
        prehlad, dnes, vcera = priprav_prehľad(df)
        zobraz_prehľad(prehlad, dnes, vcera)


if __name__ == "__main__":
    main()
