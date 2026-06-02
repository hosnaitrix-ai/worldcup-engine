import sys
import time
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
# CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL
# =========================================================
st.set_page_config(
    page_title="LiveScanner Pro - Multi-Liga Online",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
    h1 { font-weight: 900 !important; color: #0F172A; letter-spacing: -1px; }
    h3 { font-weight: 700 !important; color: #1E293B; margin-bottom: 0.5rem; }
    .match-box { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .match-header { font-size: 12px; color: #64748B; font-weight: 600; text-transform: uppercase; margin-bottom: 0.8rem; border-bottom: 1px solid #F1F5F9; padding-bottom: 4px; display: flex; justify-content: space-between; }
    .league-badge { background: #F1F5F9; color: #4338CA; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .team-name { font-size: 1.25rem; font-weight: 700; color: #1E293B; }
    .vs-badge { font-size: 10px; background: #F1F5F9; color: #64748B; padding: 2px 8px; border-radius: 4px; margin: 0 10px; font-weight: bold; }
    .market-title { font-size: 11px; font-weight: bold; color: #475569; text-transform: uppercase; text-align: center; margin-bottom: 4px; }
    .odd-box-back { background: #E0F2FE; border: 1px solid #7DD3FC; color: #0369A1; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .odd-box-lay { background: #FCE7F3; border: 1px solid #FBCFE8; color: #B91C1C; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .odd-box-goals { background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .value-badge { background: #4338CA; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 13px; display: inline-block; }
    .value-report-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }
    .report-topic { font-size: 12px; font-weight: 700; color: #4338CA; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
    .report-text { font-size: 12.5px; color: #334155; line-height: 1.5; margin-bottom: 4px; }
    .badge-value { background: #DCFCE7; color: #15803D; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; border: 1px solid #BBF7D0; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p style="color:#6366F1; font-weight:bold; text-transform:uppercase; font-size:12px; margin-bottom:0;">⚡ LiveScanner & Probability Engine</p>', unsafe_allow_html=True)
st.title("📊 ANÁLISE DE FUTEBOL - By Freed Cesar")
st.markdown("---")

# =========================================================
# DICIONÁRIO DE CONFIGURAÇÃO DE LIGAS
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
# MOTOR DE CAPTURA
# =========================================================
@st.cache_data(ttl=600)
def carregar_dados_online():
    todos_jogos = []
    
    # 1. Captura jogos futuros
    for nome_liga, config in LIGAS_MAPA.items():
        time.sleep(1.0) 
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?limit=100"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code != 200: continue
            data = response.json()
            
            for event in data.get('events', []):
                status_type = event['status']['type']['name']
                # Se for jogo passado ou futuro, vamos pegar todos para análise posterior
                date_utc = pd.to_datetime(event['date'])
                date_local = date_utc.tz_convert('America/Sao_Paulo')
                date_raw = date_local.replace(tzinfo=None)
                
                comp = event['competitions'][0]
                home_node = comp['competitors'][0]
                away_node = comp['competitors'][1]
                h_team = home_node['team']['displayName'] if home_node['homeAway'] == 'home' else away_node['team']['displayName']
                a_team = away_node['team']['displayName'] if away_node['homeAway'] == 'away' else home_node['team']['displayName']
                
                # Se for passado (status final) pega placar, se for futuro marca como NaN
                if status_type in ["STATUS_FULL_TIME", "STATUS_FINAL"]:
                    h_score = int(home_node['score']) if home_node['homeAway'] == 'home' else int(away_node['score'])
                    a_score = int(away_node['score']) if away_node['homeAway'] == 'away' else int(home_node['score'])
                    uid = f"HIST_{nome_liga}_{date_raw.strftime('%d%m%Y')}_{h_team}"
                    gols_h, gols_a = h_score, a_score
                else:
                    uid = f"FUT_{nome_liga}_{date_raw.strftime('%d%m%Y')}_{h_team}"
                    gols_h, gols_a = np.nan, np.nan
                
                todos_jogos.append({
                    "UID": uid, "League": nome_liga, "Date": date_raw, "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "Time": date_raw.strftime("%H:%M"), "Home": h_team, "Away": a_team,
                    "GOLS_HOME": gols_h, "GOLS_AWAY": gols_a, "Status": status_type
                })
        except: continue
            
    df = pd.DataFrame(todos_jogos)
    if not df.empty:
        df = df.drop_duplicates(subset=["UID"], keep='first')
    return df

df = carregar_dados_online()

if df.empty:
    st.error("Nenhum dado pôde ser coletado das APIs online neste momento.")
    st.stop()

# =========================================================
# SEPARAÇÃO DINÂMICA
# =========================================================
df_future = df[df["GOLS_HOME"].isna()].copy()
df_hist = df[df["GOLS_HOME"].notna()].copy()

# =========================================================
# FUNÇÕES DE CÁLCULO (Mantidas)
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga_jogo, l_home_mean, l_away_mean):
    if df_hist.empty: return 1.0, 1.0
    jogos = df_hist[(df_hist["Date"] < data_ref) & (df_hist["League"] == liga_jogo)].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    if len(t) == 0: return 1.0, 1.0
    t.loc[:, "peso"] = peso_temporal(t["Date"], data_ref)
    if side == "home":
        ataque = min(max(np.average(t["GOLS_HOME"], weights=t["peso"]) / l_home_mean, 0.5), 2.5)
        defesa = min(max(np.average(t["GOLS_AWAY"], weights=t["peso"]) / l_away_mean, 0.5), 2.5)
    else:
        ataque = min(max(np.average(t["GOLS_AWAY"], weights=t["peso"]) / l_away_mean, 0.5), 2.5)
        defesa = min(max(np.average(t["GOLS_HOME"], weights=t["peso"]) / l_home_mean, 0.5), 2.5)
    return ataque, defesa

def dixon_coles(lh, la, rho=-0.1, max_g=10):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)
    m[0, 0] *= (1 - lh * la * rho)
    m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho)
    m[1, 1] *= (1 - rho)
    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg, home, away):
    if hw > 62.0: return f"🔥 A favor do Mandante: Vitória do {home}"
    if aw > 45.0: return f"🚀 A favor do Visitante: Vitória do {away}"
    if o25 > 57.0 and xg > 2.8: return "⚽ Jogo de Gols: Mais de 2.5 Gols"
    if d > 31.0 and u35 > 78.0 and xg < 2.25: return "🔒 Contra o Empate / Jogo Truncado"
    if o15 > 82.0 and o25 <= 57.0: return "🛡️ Segurança: Mais de 1.5 Gols"
    return "⚖️ Sem viés claro (Fique de Fora)"

def obter_melhor_opcao_anytime(p, home, away):
    opcoes = {
        f"1-0 favor {home} a Qualquer Momento": p[1:, 0:].sum() * 100,  
        f"0-1 favor {away} a Qualquer Momento": p[0:, 1:].sum() * 100,  
        f"1-1 a Qualquer Momento": p[1:, 1:].sum() * 100                
    }
    melhor_label = max(opcoes, key=opcoes.get)
    return melhor_label, opcoes[melhor_label]

# =========================================================
# EXIBIÇÃO DO SCANNER E SELETOR DE DATAS (AJUSTADO)
# =========================================================
st.subheader("📊 Scanner de Mercado & Sinais Ativos")

if not df_future.empty:
    saida = []
    # Cálculo das probabilidades (Mantido)
    for _, r in df_future.iterrows():
        data_ref = r["Date"]
        home = r["Home"]
        away = r["Away"]
        liga_corrente = r["League"]

        df_hist_liga = df_hist[df_hist["League"] == liga_corrente]
        l_h_m = max(df_hist_liga["GOLS_HOME"].mean(), 1.2) if not df_hist_liga.empty else LIGAS_MAPA[liga_corrente]["base_home"]
        l_a_m = max(df_hist_liga["GOLS_AWAY"].mean(), 1.0) if not df_hist_liga.empty else LIGAS_MAPA[liga_corrente]["base_away"]

        ah, dh = forca_time(home, "home", data_ref, liga_corrente, l_h_m, l_a_m)
        aa, da = forca_time(away, "away", data_ref, liga_corrente, l_h_m, l_a_m)
        xg_h, xg_a = np.clip((ah * da * l_h_m), 0.3, 2.6), np.clip((aa * dh * l_a_m), 0.3, 2.4)
        p = dixon_coles(xg_h, xg_a)
        
        home_win, draw, away_win = np.sum(np.tril(p, -1)) * 100, np.sum(np.diag(p)) * 100, np.sum(np.triu(p, 1)) * 100
        max_g = p.shape[0]
        gols_c = np.array([np.sum([p[i, j] for i in range(max_g) for j in range(max_g) if i + j == k]) for k in range(21)])
        over15, over25, under35 = (1 - gols_c[0] - gols_c[1]) * 100, (1 - np.sum(gols_c[:3])) * 100, np.sum(gols_c[:4]) * 100
        xg_total = xg_h + xg_a
        sugestao = detectar_melhor_valor(home_win, draw, away_win, over15, over25, under35, xg_total, home, away)
        lbl, prob = obter_melhor_opcao_anytime(p, home, away)

        saida.append({
            "Date": r["DateStr"], "DateObj": r["Date"], "Time": r["Time"], "Home": home, "Away": away, "League": liga_corrente,
            "💡 Sugestão Value": sugestao, "anytime_label": lbl, "anytime_prob": prob, "anytime_odd": 100 / max(prob, 1.0),
            "Over 1.5 %": round(over15, 1), "Over 2.5 %": round(over25, 1), "Under 3.5 %": round(under35, 1),
            "Home Win %": round(home_win, 1), "Draw %": round(draw, 1), "Away Win %": round(away_win, 1), "Expected Goals": round(xg_total, 2)
        })

    df_proj = pd.DataFrame(saida)
    # Seleção de datas correta
    datas_unicas = sorted(df_proj["DateObj"].unique())
    opcoes_datas = [d.strftime("%d/%m/%Y") for d in datas_unicas]
    
    col_sel, _ = st.columns([1, 3])
    with col_sel:
        data_selecionada = st.selectbox("🎯 Filtrar Rodada:", opcoes_datas)

    for _, jogo in df_proj[df_proj["Date"] == data_selecionada].iterrows():
        st.markdown(f"""
        <div class="match-box">
            <div class="match-header"><span>{jogo['Date']} - {jogo['Time']}</span><span class="league-badge">{jogo['League']}</span></div>
            <div class="team-name">{jogo['Home']} VS {jogo['Away']}</div>
            <div style="margin-top: 10px;"><span class="value-badge">{jogo['💡 Sugestão Value']}</span></div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Nenhum jogo futuro encontrado.")
