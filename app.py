import sys
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

# Correção preventiva para o loop de eventos assíncronos no Windows
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configuração da Página para Mobile e Desktop
st.set_page_config(page_title="World Cup Quantum Engine", page_icon="⚡", layout="wide")

# CSS Institucional Dark Avançado
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #060913; color: #F0F4F8; }
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    footer {visibility: hidden;}
    [data-testid="stHeader"] { background: rgba(6, 9, 19, 0.8); backdrop-filter: blur(8px); }
    .main-title { font-size: 2.5rem; font-weight: 900; background: linear-gradient(90deg, #38BDF8 0%, #818CF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .kpi-wrapper { display: flex; gap: 1.2rem; margin-top: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .kpi-card-premium { background: #0F172A; padding: 1.2rem 1.5rem; border-radius: 14px; border: 1px solid #1E293B; min-width: 240px; flex: 1; border-left: 5px solid #6366F1; }
    .kpi-title-premium { font-size: 11px; text-transform: uppercase; color: #64748B; letter-spacing: 2px; font-weight: 700; margin-bottom: 4px; }
    .kpi-value-premium { font-size: 1.8rem; font-weight: 800; color: #F8FAFC; }
    .match-container-premium { background: linear-gradient(180deg, #0F172A 0%, #090D1A 100%); border: 1px solid #1E293B; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.2rem; }
    .match-meta-premium { font-size: 10px; color: #475569; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-bottom: 1.2rem; display: flex; justify-content: space-between; }
    .team-row { display: flex; align-items: center; gap: 12px; font-size: 1.4rem; font-weight: 800; color: #F1F5F9; }
    .vs-sign { font-size: 10px; font-weight: 900; color: #475569; background: #1E293B; padding: 3px 6px; border-radius: 4px; }
    .odds-matrix-premium { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-top: 0.5rem; }
    .odd-slot-premium { background: #141B2D; padding: 10px 4px; border-radius: 8px; text-align: center; border: 1px solid #1E293B; }
    .odd-name-premium { font-size: 9px; color: #64748B; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }
    .val-home-away { font-size: 13px; font-weight: 800; color: #38BDF8; }
    .val-draw { font-size: 13px; font-weight: 800; color: #94A3B8; }
    .val-goals { font-size: 13px; font-weight: 800; color: #34D399; }
    .val-btts { font-size: 13px; font-weight: 800; color: #FB7185; }
    .badge-signal-premium { background: linear-gradient(135deg, #312E81 0%, #4338CA 100%); color: #E0E7FF; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 12px; display: inline-block; margin-top: 1rem; border: 1px solid #4F46E5; }
    
    /* Estilização limpa do seletor de datas */
    .stSelectbox label { color: #94A3B8 !important; font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p style="color:#6366F1; font-weight:bold; text-transform:uppercase; font-size:11px; margin-bottom:0; letter-spacing: 2.5px;">⚡ LIVE API QUANTUM ENGINE ACTIVATED</p>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">⚽ World Cup Live Scanner</h1>', unsafe_allow_html=True)

# =========================================================
# CONSUMO DA API DA ESPN (ONLINE)
# =========================================================
@st.cache_data(ttl=900) # Atualiza a API automaticamente a cada 15 minutos
def carregar_dados_espn():
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        jogos_lista = []
        
        for event in data.get('events', []):
            status_type = event['status']['type']['name']
            date_raw = pd.to_datetime(event['date'])
            
            comp = event['competitions'][0]
            home_node = comp['competitors'][0]
            away_node = comp['competitors'][1]
            
            h_team = home_node['team']['displayName'] if home_node['homeAway'] == 'home' else away_node['team']['displayName']
            a_team = away_node['team']['displayName'] if away_node['homeAway'] == 'away' else home_node['team']['displayName']
            
            h_score = np.nan
            a_score = np.nan
            
            if status_type in ["STATUS_FULL_TIME", "STATUS_FINAL"]:
                h_score = int(home_node['score']) if home_node['homeAway'] == 'home' else int(away_node['score'])
                a_score = int(away_node['score']) if away_node['homeAway'] == 'away' else int(home_node['score'])

            jogos_lista.append({
                "DateObj": date_raw,
                "DateStr": date_raw.strftime("%d/%m/%Y"),
                "TimeStr": date_raw.strftime("%H:%M"),
                "Home": str(h_team).strip(),
                "Away": str(a_team).strip(),
                "GOLS_HOME": h_score,
                "GOLS_AWAY": a_score
            })
            
        df = pd.DataFrame(jogos_lista)
        if not df.empty:
            df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]
        return df
    except Exception as e:
        return pd.DataFrame(columns=["DateObj", "DateStr", "TimeStr", "Home", "Away", "GOLS_HOME", "GOLS_AWAY", "TOTALGOALS"])

df_raw = carregar_dados_espn()

if df_raw.empty:
    st.error("Não foi possível coletar dados da API da ESPN neste momento. O servidor pode estar indisponível.")
    st.stop()

# Separação Cirúrgica entre Histórico Real e Prospecção Futura
df_hist = df_raw[df_raw["GOLS_HOME"].notna()].copy()
df_future = df_raw[df_raw["GOLS_HOME"].isna()].copy()

# Médias Fairline Globais Dinâmicas
liga_home = max(df_hist["GOLS_HOME"].mean(), 1.45) if not df_hist.empty else 1.55
liga_away = max(df_hist["GOLS_AWAY"].mean(), 1.15) if not df_hist.empty else 1.20

# =========================================================
# POISSON & DIXON COLES ENGINE
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref):
    if df_hist.empty: return 1.0, 1.0
    jogos = df_hist[df_hist["DateObj"] < data_ref].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    if len(t) == 0: return 1.0, 1.0
    
    t.loc[:, "peso"] = peso_temporal(t["DateObj"], data_ref)
    if side == "home":
        atk = np.average(t["GOLS_HOME"], weights=t["peso"])
        def_ = np.average(t["GOLS_AWAY"], weights=t["peso"])
        return (atk / liga_home), (def_ / liga_away)
    else:
        atk = np.average(t["GOLS_AWAY"], weights=t["peso"])
        def_ = np.average(t["GOLS_HOME"], weights=t["peso"])
        return (atk / liga_away), (def_ / liga_home)

def dixon_coles(lh, la, rho=-0.05, max_g=8):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)
    m[0, 0] *= (1 - lh * la * rho); m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho); m[1, 1] *= (1 - rho)
    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, btts, xg, home, away):
    if d > 33.0 and u35 > 74.0 and xg < 2.15: return "🔒 CONTRA O EMPATE (Jogo Equilibrado)"
    if btts > 53.0 and o25 > 53.0: return "🎯 AMBOS MARCAM (BTTS) Ativo"
    if hw > 58.0: return f"🔥 VITÓRIA DO MANDANTE: {home}"
    if aw > 42.0: return f"🚀 VITÓRIA DO VISITANTE: {away}"
    if o25 > 55.0 and xg > 2.70: return "⚽ MAIS DE 2.5 GOLS"
    if o15 > 78.0 and o25 <= 55.0: return "🛡️ SEGURANÇA: Mais de 1.5 Gols"
    return "⚖️ SEM ENTRADA DE VALOR"

# =========================================================
# RENDERIZAÇÃO DO DASHBOARD PRINCIPAL
# =========================================================
media_gols_val = df_hist['TOTALGOALS'].mean() if not df_hist.empty else 2.75

st.markdown(f"""
    <div class="kpi-wrapper">
        <div class="kpi-card-premium" style="border-left-color: #38BDF8;">
            <div class="kpi-title-premium">Total de Jogos Identificados</div>
            <div class="kpi-value-premium">{len(df_raw)}</div>
        </div>
        <div class="kpi-card-premium" style="border-left-color: #A78BFA;">
            <div class="kpi-title-premium">Confrontos Futuros Mapeados</div>
            <div class="kpi-value-premium">{len(df_future)}</div>
        </div>
        <div class="kpi-card-premium" style="border-left-color: #34D399;">
            <div class="kpi-title-premium">Média Gols (Base Real)</div>
            <div class="kpi-value-premium">{media_gols_val:.2f}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# =========================================================
# INTERFACE DE FILTRO DE DATAS (APENAS JOGOS FUTUROS)
# =========================================================
if not df_future.empty:
    # Captura as datas únicas futuras e ordena de forma cronológica
    df_future_ordenado = df_future.sort_values(by="DateObj")
    datas_futuras_disponiveis = df_future_ordenado["DateStr"].unique().tolist()
    
    st.markdown("### 📅 Filtragem Avançada de Mercado")
    col_filtro, _ = st.columns([1, 2])
    with col_filtro:
        data_selecionada = st.selectbox("🎯 Escolha uma Data para Escanear:", datas_futuras_disponiveis)
    
    # Filtra os dados apenas para a data que o usuário escolheu
    df_filtrado_dia = df_future[df_future["DateStr"] == data_selecionada]
    
    # Processamento matemático e geração dos Cards
    saida = []
    for _, r in df_filtrado_dia.iterrows():
        home, away, data_ref, hora_jogo = r["Home"], r["Away"], r["DateObj"], r["TimeStr"]
        ah, dh = forca_time(home, "home", data_ref)
        aa, da = forca_time(away, "away", data_ref)
        
        xg_h = np.clip((ah * da * liga_home), 0.2, 3.8)
        xg_a = np.clip((aa * dh * liga_away), 0.2, 3.5)
        
        p = dixon_coles(xg_h, xg_a)
        hw = np.sum(np.tril(p, -1)) * 100
        d = np.sum(np.diag(p)) * 100
        aw = np.sum(np.triu(p, 1)) * 100
        
        g_comb = np.array([np.sum([p[i, j] for i in range(p.shape[0]) for j in range(p.shape[0]) if i + j == k]) for k in range(15)])
        o15, o25, u35 = (1 - g_comb[0] - g_comb[1]) * 100, (1 - np.sum(g_comb[:3])) * 100, np.sum(g_comb[:4]) * 100
        btts = np.sum(p[1:, 1:]) * 100
        xg_t = xg_h + xg_a
        
        sugestao = detectar_melhor_valor(hw, d, aw, o15, o25, u35, btts, xg_t, home, away)
        
        saida.append({
            "Match": f"{home} x {away}", "Hora": hora_jogo, "Sugestao": sugestao, 
            "HomeWin": hw, "Draw": d, "AwayWin": aw, "O15": o15, "O25": o25, "U35": u35, "BTTS": btts, "xG": xg_t
        })

    st.markdown(f"### 🔮 Sinais Ativos para o Dia {data_selecionada}")
    for j in saida:
        st.markdown(f"""
        <div class="match-container-premium">
            <div class="match-meta-premium">
                <span>⏰ HORÁRIO INICIAL: {j['Hora']}</span>
                <span>xG Estimado: {j['xG']:.2f}</span>
            </div>
            <div class="team-row"><span>{j['Match']}</span></div>
            <div class="badge-signal-premium">{j['Sugestao']}</div>
            <div class="odds-matrix-premium">
                <div class="odd-slot-premium"><div class="odd-name-premium">Casa</div><div class="val-home-away">{j['HomeWin']:.1f}%</div></div>
                <div class="odd-slot-premium"><div class="odd-name-premium">Empate</div><div class="val-draw">{j['Draw']:.1f}%</div></div>
                <div class="odd-slot-premium"><div class="odd-name-premium">Fora</div><div class="val-home-away">{j['AwayWin']:.1f}%</div></div>
                <div class="odd-slot-premium"><div class="odd-name-premium">O1.5</div><div class="val-goals">{j['O15']:.1f}%</div></div>
                <div class="odd-slot-premium"><div class="odd-name-premium">O2.5</div><div class="val-goals">{j['O25']:.1f}%</div></div>
                <div class="odd-slot-premium"><div class="odd-name-premium">U3.5</div><div class="val-goals">{j['U35']:.1f}%</div></div>
                <div class="odd-slot-premium"><div class="odd-name-premium">BTTS</div><div class="val-btts">{j['BTTS']:.1f}%</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Todos os jogos recebidos pela API para esta chave de competição já foram encerrados. Não há partidas futuras agendadas neste momento.")
