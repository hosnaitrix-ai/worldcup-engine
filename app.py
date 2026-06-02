import streamlit as st
import requests
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(layout="wide", page_title="LiveScanner Pro - Multi-Liga")

# Dicionário Completo de Ligas
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

@st.cache_data(ttl=3600)
def carregar_dados_full():
    todos_eventos = []
    # Janela de 7 dias para garantir cobertura total das rodadas
    datas = pd.date_range(start=pd.Timestamp.now(), periods=7)
    
    for nome_liga, config in LIGAS_MAPA.items():
        for data in datas:
            d_str = data.strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?dates={d_str}"
            try:
                resp = requests.get(url, timeout=3).json()
                if 'events' in resp:
                    for e in resp['events']:
                        comp = e['competitors'][0]
                        todos_eventos.append({
                            "Liga": nome_liga,
                            "Data": data.strftime("%d/%m/%Y"),
                            "Home": comp['competitors'][0]['team']['displayName'],
                            "Away": comp['competitors'][1]['team']['displayName']
                        })
            except: continue
    return pd.DataFrame(todos_eventos)

# Interface do App
st.title("⚡ LiveScanner - Multi-Liga Engine")
df = carregar_dados_full()

if not df.empty:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        data_sel = st.selectbox("Selecione a Data:", sorted(df['Data'].unique()))
    with col2:
        # Filtra ligas disponíveis para a data selecionada
        ligas_disp = df[df['Data'] == data_sel]['Liga'].unique()
        liga_sel = st.selectbox("Selecione a Liga:", ligas_disp)
    
    st.markdown("---")
    
    jogos = df[(df['Data'] == data_sel) & (df['Liga'] == liga_sel)]
    
    if not jogos.empty:
        for _, row in jogos.iterrows():
            st.markdown(f"""
            <div style="background:#FFFFFF; padding:15px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:10px;">
                <h4 style="margin:0; color:#1E293B;">{row['Home']} <span style="color:#64748B;">vs</span> {row['Away']}</h4>
                <p style="color:#4338CA; font-size:12px; font-weight:bold; margin-top:5px;">
                    PRONTO PARA PROJEÇÃO QUANTITATIVA
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum jogo encontrado para esta seleção.")
else:
    st.error("Não foi possível conectar às fontes de dados. Tente novamente em instantes.")
