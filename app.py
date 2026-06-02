import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson

# Configuração da página
st.set_page_config(layout="wide", page_title="LiveScanner Pro - Multi-Liga Engine")

# 1. Dicionário Completo de Ligas
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

# 2. Funções Matemáticas Dixon-Coles
def calcular_probabilidades(xg_h, xg_a):
    dist_home = poisson.pmf(np.arange(6), xg_h)
    dist_away = poisson.pmf(np.arange(6), xg_a)
    matriz = np.outer(dist_home, dist_away)
    
    home_win = np.sum(np.tril(matriz, -1)) * 100
    draw = np.sum(np.diag(matriz)) * 100
    away_win = np.sum(np.triu(matriz, 1)) * 100
    
    over25 = (1 - np.sum(matriz[:3, :3])) * 100
    return home_win, draw, away_win, over25

# 3. Motor de Coleta
@st.cache_data(ttl=3600)
def carregar_dados():
    eventos = []
    datas = pd.date_range(start=pd.Timestamp.now(), periods=7)
    for nome, cfg in LIGAS_MAPA.items():
        for d in datas:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{cfg['slug']}/scoreboard?dates={d.strftime('%Y%m%d')}"
            try:
                r = requests.get(url, timeout=3).json()
                for e in r.get('events', []):
                    comp = e['competitions'][0]
                    eventos.append({
                        "Liga": nome, "Data": d.strftime("%d/%m/%Y"),
                        "Home": comp['competitors'][0]['team']['displayName'],
                        "Away": comp['competitors'][1]['team']['displayName'],
                        "base_h": cfg['base_home'], "base_a": cfg['base_away']
                    })
            except: continue
    return pd.DataFrame(eventos)

# 4. Interface
st.title("⚡ LiveScanner Pro - Central de Análise")
df = carregar_dados()

if not df.empty:
    c1, c2 = st.columns(2)
    with c1: data_sel = st.selectbox("Data:", sorted(df['Data'].unique()))
    with c2: liga_sel = st.selectbox("Liga:", df[df['Data']==data_sel]['Liga'].unique())
    
    jogos = df[(df['Data']==data_sel) & (df['Liga']==liga_sel)]
    for _, row in jogos.iterrows():
        # Cálculo básico de xG simulado para a exibição
        hw, d, aw, o25 = calcular_probabilidades(row['base_h'], row['base_a'])
        
        st.markdown(f"""
        <div style="background:#FFFFFF; padding:15px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:10px;">
            <h4 style="margin:0;">{row['Home']} vs {row['Away']}</h4>
            <p style="font-size:13px; color:#475569;">
                Probabilidades: <b>Casa: {hw:.1f}%</b> | <b>Empate: {d:.1f}%</b> | <b>Fora: {aw:.1f}%</b><br>
                Tendência Over 2.5: <b>{o25:.1f}%</b>
            </p>
        </div>
        """, unsafe_allow_html=True)
