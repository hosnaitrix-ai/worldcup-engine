import sys
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

st.set_page_config(page_title="LiveScanner Pro - Multi-Liga", layout="wide")

# =========================================================
# CONFIGURAÇÃO DE LIGAS (TODAS AS 17 SOLICITADAS)
# =========================================================
LIGAS_MAPA = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Brasileirão - Feminino": {"slug": "bra.women.1", "base_home": 1.58, "base_away": 1.18},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
    "Finlândia - Veikkausliiga": {"slug": "fin.1", "base_home": 1.48, "base_away": 1.18},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Suécia - Superettan": {"slug": "swe.2", "base_home": 1.55, "base_away": 1.20},
    "Suécia - Damallsvenskan": {"slug": "swe.women.1", "base_home": 1.85, "base_away": 1.40},
    "Noruega - Eliteserien": {"slug": "nor.1", "base_home": 1.70, "base_away": 1.35},
    "Chile - Primera División": {"slug": "chi.1", "base_home": 1.50, "base_away": 1.12},
    "Equador - LigaPro": {"slug": "ecu.1", "base_home": 1.60, "base_away": 1.10},
    "EUA - MLS": {"slug": "usa.1", "base_home": 1.68, "base_away": 1.30},
    "UEFA Champions League": {"slug": "champions", "base_home": 1.65, "base_away": 1.30},
    "Copa Libertadores": {"slug": "libertadores", "base_home": 1.45, "base_away": 1.05},
    "Copa Sudamericana": {"slug": "sudamericana", "base_home": 1.35, "base_away": 0.95},
    "Copa do Mundo 2026": {"slug": "fifa.world.cup", "base_home": 1.52, "base_away": 1.18}
}

# =========================================================
# MOTOR DE CAPTURA OTIMIZADO
# =========================================================
@st.cache_data(ttl=600)
def carregar_dados_online():
    todos_jogos = []
    datas_alvo = [pd.Timestamp.now().normalize() + pd.Timedelta(days=i) for i in range(14)]
    
    for nome_liga, config in LIGAS_MAPA.items():
        for data in datas_alvo:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?dates={data.strftime('%Y%m%d')}"
            try:
                resp = requests.get(url, timeout=5).json()
                for event in resp.get('events', []):
                    comp = event['competitions'][0]
                    h_team = comp['competitors'][0]['team']['displayName']
                    a_team = comp['competitors'][1]['team']['displayName']
                    todos_jogos.append({
                        "League": nome_liga, "Date": data, "DateStr": data.strftime("%d/%m/%Y"),
                        "Home": h_team, "Away": a_team, "GOLS_HOME": np.nan, "GOLS_AWAY": np.nan
                    })
            except: continue
    return pd.DataFrame(todos_jogos)

# Interface Principal
st.title("📊 Scanner Profissional - Freed Cesar")
df = carregar_dados_online()

# Filtro de Liga no topo para organizar a tela
liga_selecionada = st.selectbox("Selecione a Liga para Análise:", list(LIGAS_MAPA.keys()))
df_filtrado = df[df['League'] == liga_selecionada]

if not df_filtrado.empty:
    st.write(f"Analisando {len(df_filtrado)} eventos para {liga_selecionada}...")
    # (A lógica de cálculo Dixon-Coles que você já possui continuaria aqui abaixo)
else:
    st.warning("Nenhum jogo encontrado para esta liga nos próximos 14 dias.")
