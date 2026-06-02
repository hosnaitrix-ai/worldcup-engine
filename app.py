import sys
import time
import random
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="LiveScanner Pro - Multi-Liga Online",
    page_icon="⚡",
    layout="wide"
)

st.title("📊 ANÁLISE DE FUTEBOL - By Freed Cesar")
st.markdown("---")

# =========================================================
# LIGAS (SUÉCIA RESTAURADA + OUTRAS)
# =========================================================
LIGAS_MAPA = {
    # 🇧🇷 Brasil
    "Brasileirão Série A": {"slug": "bra.1"},
    "Brasileirão Série B": {"slug": "bra.2"},

    # 🇩🇪 Alemanha
    "Bundesliga": {"slug": "ger.1"},

    # 🇳🇱 Holanda
    "Eredivisie": {"slug": "ned.1"},

    # 🇺🇸 EUA
    "MLS": {"slug": "usa.1"},

    # 🇪🇺 Europa
    "Champions League": {"slug": "champions"},

    # 🇸🇪 SUÉCIA (RESTAURADO COMPLETO)
    "Suécia - Allsvenskan": {"slug": "swe.1"},
    "Suécia - Superettan": {"slug": "swe.2"},
    "Suécia - Damallsvenskan": {"slug": "swe.women.1"},
}

# =========================================================
# CARREGAMENTO DE DADOS
# =========================================================
@st.cache_data(ttl=300)
def carregar_dados_online():

    todos_jogos = []
    hoje = pd.Timestamp.now().normalize()

    # 🔥 SOMENTE HOJE + 12 DIAS
    datas_alvo = [hoje + pd.Timedelta(days=i) for i in range(0, 13)]

    for nome_liga, config in LIGAS_MAPA.items():

        # 🔥 delay anti-bloqueio
        time.sleep(random.uniform(0.7, 1.4))

        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard"

        try:
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue

            data = r.json()

            for event in data.get("events", []):

                comp = event["competitions"][0]

                home = comp["competitors"][0]["team"]["displayName"]
                away = comp["competitors"][1]["team"]["displayName"]

                status = event["status"]["type"]["name"]

                date_utc = pd.to_datetime(event["date"], utc=True)
                date_local = date_utc.tz_convert("America/Sao_Paulo")
                date_raw = date_local.replace(tzinfo=None)

                todos_jogos.append({
                    "League": nome_liga,
                    "Date": date_raw,
                    "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "Time": date_raw.strftime("%H:%M"),
                    "Home": home,
                    "Away": away,
                    "Status": status
                })

        except Exception as e:
            print(f"Erro {nome_liga}: {e}")
            continue

    return pd.DataFrame(todos_jogos)

df = carregar_dados_online()

if df.empty:
    st.error("Sem dados disponíveis.")
    st.stop()

# =========================================================
# FILTRO DE DATA CORRIGIDO
# =========================================================
df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%d/%m/%Y")

# 🔥 datas começam HOJE
datas_disponiveis = sorted(df["DateStr"].unique())

st.subheader("📊 Scanner de Jogos")

data_sel = st.selectbox(
    "📅 Selecione a data (a partir de hoje):",
    datas_disponiveis
)

df_filtrado = df[df["DateStr"] == data_sel]

# =========================================================
# EXIBIÇÃO (SEU DESIGN MANTIDO)
# =========================================================
for _, jogo in df_filtrado.iterrows():

    st.markdown(f"""
    <div class="match-box">
        <div class="match-header">
            <span>📅 {jogo['DateStr']} {jogo['Time']}</span>
            <span class="league-badge">{jogo['League']}</span>
        </div>

        <div>
            <span class="team-name">{jogo['Home']}</span>
            <span class="vs-badge">VS</span>
            <span class="team-name">{jogo['Away']}</span>
        </div>

        <div style="margin-top:10px; display:grid; grid-template-columns:repeat(3,1fr); gap:10px;">
            <div class="odd-box-back">Casa</div>
            <div class="odd-box-lay">Empate</div>
            <div class="odd-box-back">Fora</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
