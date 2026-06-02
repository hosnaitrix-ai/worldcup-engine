import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson

# Configuração da página
st.set_page_config(layout="wide", page_title="LiveScanner Pro")

# Mapeamento oficial das ligas
LIGAS_MAPA = {
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Suécia - Superettan": {"slug": "swe.2", "base_home": 1.55, "base_away": 1.20}
}

@st.cache_data(ttl=3600)
def carregar_dados_full():
    todos_eventos = []
    # Janela de 10 dias para garantir o espectro do dia 09/06
    datas = pd.date_range(start="2026-06-02", periods=10)
    
    for nome_liga, config in LIGAS_MAPA.items():
        for data in datas:
            d_str = data.strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?dates={d_str}"
            try:
                resp = requests.get(url, timeout=5).json()
                if 'events' in resp:
                    for e in resp['events']:
                        comp = e['competitions'][0]
                        todos_eventos.append({
                            "Liga": nome_liga,
                            "Data": data.strftime("%d/%m/%Y"),
                            "Home": comp['competitors'][0]['team']['displayName'],
                            "Away": comp['competitors'][1]['team']['displayName']
                        })
            except: continue
    return pd.DataFrame(todos_eventos)

# Interface
st.title("⚡ LiveScanner - Projeções Quantitativas")
df = carregar_dados_full()

if not df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        data_sel = st.selectbox("Selecione a Data:", sorted(df['Data'].unique()))
    with col2:
        ligas_disp = df[df['Data'] == data_sel]['Liga'].unique()
        liga_sel = st.selectbox("Selecione a Liga:", ligas_disp)
    
    st.markdown("---")
    
    jogos = df[(df['Data'] == data_sel) & (df['Liga'] == liga_sel)]
    
    if not jogos.empty:
        for _, row in jogos.iterrows():
            st.markdown(f"""
            <div style="background:#F8FAFC; padding:15px; border-radius:10px; border-left:5px solid #3B82F6; margin-bottom:10px;">
                <h4 style="margin:0;">{row['Home']} vs {row['Away']}</h4>
                <p style="color:#64748B; font-size:14px;">Status: Aguardando Cálculo Dixon-Coles | Data: {row['Data']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum jogo encontrado nesta combinação.")
else:
    st.error("Falha ao conectar com os servidores. Verifique sua conexão.")
