import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson

# Configuração da página
st.set_page_config(layout="wide", page_title="LiveScanner Pro - Completo")

# Dicionário de Ligas
LIGAS_MAPA = {
    "Brasileirão - Série A": "bra.1", "Brasileirão - Série B": "bra.2", 
    "Brasileirão - Feminino": "bra.women.1", "Alemanha - Bundesliga": "ger.1",
    "Holanda - Eredivisie": "ned.1", "Finlândia - Veikkausliiga": "fin.1",
    "Suécia - Allsvenskan": "swe.1", "Suécia - Superettan": "swe.2",
    "Suécia - Damallsvenskan": "swe.women.1", "Noruega - Eliteserien": "nor.1",
    "Chile - Primera División": "chi.1", "Equador - LigaPro": "ecu.1",
    "EUA - MLS": "usa.1", "UEFA Champions League": "champions",
    "Copa Libertadores": "libertadores", "Copa Sudamericana": "sudamericana",
    "Copa do Mundo 2026": "fifa.world.cup"
}

@st.cache_data(ttl=3600)
def obter_dados_estruturados():
    eventos_futuros = []
    # Busca rodadas futuras
    datas = pd.date_range(start=pd.Timestamp.now(), periods=10)
    
    for nome, slug in LIGAS_MAPA.items():
        for d in datas:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={d.strftime('%Y%m%d')}"
            try:
                r = requests.get(url, timeout=3).json()
                for e in r.get('events', []):
                    comp = e['competitions'][0]
                    # Identificar se é jogo futuro
                    if e['status']['type']['state'] == 'pre':
                        eventos_futuros.append({
                            "Liga": nome, "Data": d.strftime("%d/%m/%Y"),
                            "Home": comp['competitors'][0]['team']['displayName'],
                            "Away": comp['competitors'][1]['team']['displayName']
                        })
            except: continue
    return pd.DataFrame(eventos_futuros)

# Lógica de Cálculo de Probabilidade (Dixon-Coles Simplificado)
def calcular_dc(h_team, a_team):
    # Aqui entra sua lógica de força baseada em gols médios
    # Como uma base fixa para o cálculo:
    xg_home = 1.45  # Você pode substituir pelo histórico extraído
    xg_away = 1.10
    
    dist_h = poisson.pmf(np.arange(5), xg_home)
    dist_a = poisson.pmf(np.arange(5), xg_away)
    matriz = np.outer(dist_h, dist_a)
    
    return {
        "Casa": np.sum(np.tril(matriz, -1)) * 100,
        "Empate": np.sum(np.diag(matriz)) * 100,
        "Fora": np.sum(np.triu(matriz, 1)) * 100
    }

# Interface
st.title("📊 LiveScanner Pro - Motor de Análise 2026")
df = obter_dados_estruturados()

if not df.empty:
    data_sel = st.selectbox("Selecione a Data:", sorted(df['Data'].unique()))
    liga_sel = st.selectbox("Selecione a Liga:", df[df['Data']==data_sel]['Liga'].unique())
    
    jogos = df[(df['Data']==data_sel) & (df['Liga']==liga_sel)]
    
    for _, row in jogos.iterrows():
        probs = calcular_dc(row['Home'], row['Away'])
        st.info(f"⚽ {row['Home']} vs {row['Away']}")
        st.write(f"Projeção: Casa {probs['Casa']:.1f}% | Empate {probs['Empate']:.1f}% | Fora {probs['Fora']:.1f}%")
else:
    st.error("Nenhum jogo encontrado para o período.")
