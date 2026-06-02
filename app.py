import sys
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson
import time

if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(page_title="LiveScanner Pro - Multi-Liga", page_icon="⚡", layout="wide")

# ... (Mantenha o seu bloco de CSS original aqui) ...

st.title("📊 ANÁLISE DE FUTEBOL - By Freed Cesar")

# =========================================================
# CONFIGURAÇÃO DAS LIGAS (AJUSTADO)
# =========================================================
LIGAS_MAPA = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Brasileirão - Série C": {"slug": "bra.3", "base_home": 1.30, "base_away": 0.90},
    "Equador - LigaPro": {"slug": "ecu.1", "base_home": 1.60, "base_away": 1.10},
    "Chile - Primera División": {"slug": "chi.1", "base_home": 1.50, "base_away": 1.12},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Suécia - Superettan": {"slug": "swe.2", "base_home": 1.55, "base_away": 1.20},
    "Suécia - Damallsvenskan": {"slug": "swe.1w", "base_home": 1.70, "base_away": 1.35},
    "Finlândia - Veikkausliiga": {"slug": "fin.1", "base_home": 1.48, "base_away": 1.18},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
    "UEFA Champions League": {"slug": "uefa.champions", "base_home": 1.60, "base_away": 1.25}
}

# =========================================================
# MOTOR DE CAPTURA ONLINE
# =========================================================
@st.cache_data(ttl=300)
def carregar_dados_online():
    todos_jogos = []
    for nome_liga, config in LIGAS_MAPA.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?dates=20260101-20261231&limit=300"
        try:
            response = requests.get(url, timeout=8)
            if response.status_code != 200: continue
            data = response.json()
            for event in data.get('events', []):
                comp = event['competitions'][0]
                status_type = event['status']['type']['name']
                date_raw = pd.to_datetime(event['date']).tz_localize(None) - pd.Timedelta(hours=3)
                
                # Tratamento de segurança para nomes de times e placares
                competitors = comp['competitors']
                home_node = next((c for c in competitors if c['homeAway'] == 'home'), None)
                away_node = next((c for c in competitors if c['homeAway'] == 'away'), None)
                
                if not home_node or not away_node: continue
                
                h_team = home_node['team']['displayName']
                a_team = away_node['team']['displayName']
                
                h_score, a_score = np.nan, np.nan
                if status_type in ["STATUS_FULL_TIME", "STATUS_FINAL"]:
                    h_score = int(home_node.get('score', 0))
                    a_score = int(away_node.get('score', 0))
                
                todos_jogos.append({
                    "League": nome_liga, "Date": date_raw, "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "Time": date_raw.strftime("%H:%M"), "Home": h_team, "Away": a_team,
                    "GOLS_HOME": h_score, "GOLS_AWAY": a_score,
                    "Score": f"{h_score}–{a_score}" if not np.isnan(h_score) else "vs"
                })
            time.sleep(0.3) # Evita bloqueio da API
        except Exception: continue
    
    df = pd.DataFrame(todos_jogos)
    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"].fillna(0) + df["GOLS_AWAY"].fillna(0)
    return df

df = carregar_dados_online()
if df.empty:
    st.error("Nenhum dado pôde ser coletado.")
    st.stop()

# ... (Mantenha o restante das funções de cálculo: peso_temporal, forca_time, etc.) ...
# ... (Mantenha o loop de exibição no streamlit) ...

# =========================================================
# CENTRAL DE LIQUIDEZ CORRIGIDA
# =========================================================
st.markdown("---")
with st.expander("🗂️ Central de Liquidez e Banco de Dados Histórico Online"):
    df_hist = df[df["GOLS_HOME"].notna()].copy()
    if not df.empty:
        liga_default = df["League"].iloc[0]
        df_hist_view = df_hist[df_hist["League"] == liga_default].copy()
    else: df_hist_view = df_hist

    # Exibição com segurança
    if not df_hist_view.empty:
        cols_exibir = ["DateStr", "Time", "Home", "Score", "Away", "TOTALGOALS", "League"]
        st.dataframe(df_hist_view[cols_exibir].sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.info("Nenhum dado histórico para exibição.")
