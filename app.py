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
st.set_page_config(page_title="LiveScanner Pro - Multi-Liga Online", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
    h1 { font-weight: 900 !important; color: #0F172A; letter-spacing: -1px; }
    h3 { font-weight: 700 !important; color: #1E293B; margin-bottom: 0.5rem; }
    .metric-card { background-color: #0F172A; padding: 1.2rem; border-radius: 8px; border-left: 4px solid #10B981; color: white; }
    .metric-title { font-size: 11px; text-transform: uppercase; color: #94A3B8; letter-spacing: 1px; font-weight: bold; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #10B981; margin-top: 2px; }
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

st.title("📊 ANÁLISE DE FUTEBOL - By Freed Cesar")

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
                status_type = event['status']['type']['name']
                date_raw = pd.to_datetime(event['date']).tz_localize(None) - pd.Timedelta(hours=3)
                comp = event['competitions'][0]
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
                    "Time": date_raw.strftime("%H:%M"), "Home": h_team.strip(), "Away": a_team.strip(),
                    "GOLS_HOME": h_score, "GOLS_AWAY": a_score,
                    "Score": f"{h_score}–{a_score}" if not np.isnan(h_score) else "vs"
                })
            time.sleep(0.3)
        except Exception: continue
    df = pd.DataFrame(todos_jogos)
    if not df.empty:
        df = df.drop_duplicates(subset=["DateStr", "Home", "Away"])
        df["TOTALGOALS"] = df["GOLS_HOME"].fillna(0) + df["GOLS_AWAY"].fillna(0)
    return df

df = carregar_dados_online()
if df.empty:
    st.error("Nenhum dado pôde ser coletado das APIs online neste momento.")
    st.stop()

hoje = pd.Timestamp.now().floor('D')
df_hist = df[df["GOLS_HOME"].notna() & (df["Date"] < hoje)].copy()
df_future = df[df["GOLS_HOME"].isna() & (df["Date"] >= hoje)].copy()

# Pré-calculo de médias para performance (Otimização)
medias_ligas = {liga: {
    "home": max(df_hist[df_hist["League"] == liga]["GOLS_HOME"].mean(), 1.0) if not df_hist[df_hist["League"] == liga].empty else LIGAS_MAPA[liga]["base_home"],
    "away": max(df_hist[df_hist["League"] == liga]["GOLS_AWAY"].mean(), 1.0) if not df_hist[df_hist["League"] == liga].empty else LIGAS_MAPA[liga]["base_away"]
} for liga in LIGAS_MAPA}

# Funções (Mantidas conforme seu original, garantindo compatibilidade)
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga_jogo, l_home_mean, l_away_mean):
    if df_hist.empty: return 1.0, 1.0
    jogos = df_hist[(df_hist["Date"] < data_ref) & (df_hist["League"] == liga_jogo)].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    if len(t) < 3: return 1.0, 1.0
    t.loc[:, "peso"] = peso_temporal(t["Date"], data_ref)
    atk = np.average(t["GOLS_HOME" if side == "home" else "GOLS_AWAY"], weights=t["peso"])
    def_ = np.average(t["GOLS_AWAY" if side == "home" else "GOLS_HOME"], weights=t["peso"])
    fator = min(len(t) / 8, 1)
    ataque = fator * (atk / (l_home_mean if side == "home" else l_away_mean)) + (1 - fator)
    defesa = fator * (def_ / (l_away_mean if side == "home" else l_home_mean)) + (1 - fator)
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
    if (aw + d) > 65.0 and aw > 25.0: return f"🛡️ Dupla Chance: {away} ou Empate"
    return "⚖️ Sem viés claro (Fique de Fora)"

def obter_melhor_opcao_anytime(p, home, away):
    opcoes = {
        f"1-0 favor {home} a Qualquer Momento": p[1:, 0:].sum() * 100,  
        f"2-0 favor {home} a Qualquer Momento": p[2:, 0:].sum() * 100,  
        f"2-1 favor {home} a Qualquer Momento": p[2:, 1:].sum() * 100,  
        f"0-1 favor {away} a Qualquer Momento": p[0:, 1:].sum() * 100,  
        f"0-2 favor {away} a Qualquer Momento": p[0:, 2:].sum() * 100,  
        f"1-1 a Qualquer Momento": p[1:, 1:].sum() * 100                
    }
    melhor_label = max(opcoes, key=opcoes.get)
    return melhor_label, opcoes[melhor_label]

# Exibição
st.subheader("📊 Scanner de Mercado & Sinais Ativos")
saida = []
if not df_future.empty:
    for _, r in df_future.iterrows():
        l_m = medias_ligas[r["League"]]
        ah, dh = forca_time(r["Home"], "home", r["Date"], r["League"], l_m["home"], l_m["away"])
        aa, da = forca_time(r["Away"], "away", r["Date"], r["League"], l_m["home"], l_m["away"])
        xg_h = np.clip((ah * da * l_m["home"]) * 0.65 + l_m["home"] * 0.35, 0.2, 2.6)
        xg_a = np.clip((aa * dh * l_m["away"]) * 0.65 + l_m["away"] * 0.35, 0.2, 2.4)
        p = dixon_coles(xg_h, xg_a)
        
        home_win, draw, away_win = np.sum(np.tril(p, -1)) * 100, np.sum(np.diag(p)) * 100, np.sum(np.triu(p, 1)) * 100
        gols_c = np.array([np.sum([p[i, j] for i in range(11) for j in range(11) if i + j == k]) for k in range(21)])
        over15, over25, under35 = (1 - gols_c[0] - gols_c[1]) * 100, (1 - np.sum(gols_c[:3])) * 100, np.sum(gols_c[:4]) * 100
        lbl, prob = obter_melhor_opcao_anytime(p, r["Home"], r["Away"])
        
        saida.append({
            "Date": r["DateStr"], "Time": r["Time"], "Home": r["Home"], "Away": r["Away"], "League": r["League"],
            "💡 Sugestão Value": detectar_melhor_valor(home_win, draw, away_win, over15, over25, under35, xg_h+xg_a, r["Home"], r["Away"]),
            "anytime_label": lbl, "anytime_prob": prob, "anytime_odd_justa": 100/max(prob, 1),
            "Over 1.5 %": round(over15, 1), "Over 2.5 %": round(over25, 1), "Under 3.5 %": round(under35, 1),
            "Home Win %": round(home_win, 1), "Draw %": round(draw, 1), "Away Win %": round(away_win, 1), "Expected Goals": round(xg_h + xg_a, 2)
        })

    df_proj = pd.DataFrame(saida)
    # Exibição simplificada para o usuário final... (restante do seu código original de exibição aqui)
    st.dataframe(df_proj) # Sugestão: manter o formato de exibição original, aqui apenas um exemplo de debug
