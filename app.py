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

st.set_page_config(page_title="LiveScanner Pro - Multi-Liga Online", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    .match-box { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; }
    .odd-box-back { background: #E0F2FE; color: #0369A1; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; }
    .odd-box-goals { background: #F0FDF4; color: #166534; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; }
    .value-badge { background: #4338CA; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 ANÁLISE DE FUTEBOL - Otimizado")

# [INSERIR SEU DICIONÁRIO LIGAS_MAPA AQUI]
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

def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga_jogo, l_home_mean, l_away_mean):
    if df_hist.empty: return 1.0, 1.0
    jogos = df_hist[(df_hist["Date"] < data_ref) & (df_hist["League"] == liga_jogo)].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    
    if len(t) < 3: t = df_hist[(df_hist["League"] == liga_jogo)].copy()
    if len(t) == 0: return 1.0, 1.0
    t.loc[:, "peso"] = peso_temporal(t["Date"], data_ref)
    
    if side == "home":
        atk = np.average(t["GOLS_HOME"], weights=t["peso"])
        defe = np.average(t["GOLS_AWAY"], weights=t["peso"])
    else:
        atk = np.average(t["GOLS_AWAY"], weights=t["peso"])
        defe = np.average(t["GOLS_HOME"], weights=t["peso"])
    
    fator = min(len(t) / 8, 1)
    ataque = fator * (atk / (l_home_mean if side == "home" else l_away_mean)) + (1 - fator)
    defesa = fator * (defe / (l_away_mean if side == "home" else l_home_mean)) + (1 - fator)
    return np.clip(ataque, 0.50, 2.20), np.clip(defesa, 0.50, 2.20)

def dixon_coles(lh, la, rho=-0.1, max_g=10):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)
    m[0, 0] *= (1 - lh * la * rho)
    m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho)
    m[1, 1] *= (1 - rho)
    return m / m.sum()

# segunda parte2

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, btts, xg, home, away):
    if hw > 62: return f"🔥 Vitória {home}"
    if aw > 45: return f"🚀 Vitória {away}"
    if o25 > 58 and xg > 2.7: return "⚽ Over 2.5"
    if btts > 58: return "🎯 BTTS SIM"
    if (aw + d) > 68: return f"🛡️ Dupla Chance {away}/Empate"
    if o15 > 82: return "🛡️ Over 1.5"
    return "⚖️ Sem Value"

# Carregamento e setup
df = carregar_dados_online()
df_future, df_hist = df[df["GOLS_HOME"].isna()].copy(), df[df["GOLS_HOME"].notna()].copy()

st.subheader("📊 Scanner de Mercado & Sinais Ativos")
if not df_hist.empty:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jogos Históricos", len(df_hist))
    c2.metric("Média Gols", round(df_hist["TOTALGOALS"].mean(), 2))
    c3.metric("Over 2.5", f"{((df_hist['TOTALGOALS']>2.5).mean()*100):.1f}%")
    c4.metric("BTTS", f"{(((df_hist['GOLS_HOME']>0)&(df_hist['GOLS_AWAY']>0)).mean()*100):.1f}%")

saida = []
for _, r in df_future.iterrows():
    # Cálculo das médias (ajustar conforme seu dicionário)
    liga_h_mean = df_hist[df_hist["League"] == r["League"]]["GOLS_HOME"].mean()
    liga_a_mean = df_hist[df_hist["League"] == r["League"]]["GOLS_AWAY"].mean()
    
    ah, dh = forca_time(r["Home"], "home", r["Date"], r["League"], liga_h_mean, liga_a_mean)
    aa, da = forca_time(r["Away"], "away", r["Date"], r["League"], liga_h_mean, liga_a_mean)
    
    xg_h = np.clip(((ah * da * liga_h_mean) * 0.65 + liga_h_mean * 0.35), 0.2, 2.6)
    xg_a = np.clip(((aa * dh * liga_a_mean) * 0.65 + liga_a_mean * 0.35), 0.2, 2.4)
    
    p = dixon_coles(xg_h, xg_a)
    btts = (1 - p[0, :].sum() - p[:, 0].sum() + p[0, 0]) * 100
    placar_correto = f"{np.unravel_index(np.argmax(p), p.shape)[0]}x{np.unravel_index(np.argmax(p), p.shape)[1]}"
    
    # ... [Manter seus cálculos de home_win, draw, away_win, over15, over25, under35]
# =========================================================
# FUNÇÕES MATEMÁTICAS E PREDITIVAS (DIXON-COLES)
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

    #FINAL DA DYXON COLES========================================

    sugestao_value = detectar_melhor_valor(home_win, draw, away_win, over15, over25, under35, btts, xg_h+xg_a, r["Home"], r["Away"])
    
    saida.append({
        "Date": r["DateStr"], "Time": r["Time"], "Home": r["Home"], "Away": r["Away"], "League": r["League"],
        "💡 Sugestão Value": sugestao_value, "BTTS %": round(btts,1), "Placar Provável": placar_correto,
        "Expected Goals": round(xg_h + xg_a, 2), "Home Win %": round(home_win, 1), "Draw %": round(draw, 1),
        "Away Win %": round(away_win, 1), "Over 1.5 %": round(over15, 1), "Over 2.5 %": round(over25, 1),
        "Under 3.5 %": round(under35, 1)
    })

    #======================PARTE 3

    # Continuação do bloco de exibição
if saida:
    df_proj = pd.DataFrame(saida)
    data_sel = st.selectbox("🎯 Filtrar Rodada:", sorted(df_proj["Date"].unique()))
    
    for _, jogo in df_proj[df_proj["Date"] == data_sel].iterrows():
        st.markdown(f"""
        <div class="match-box">
            <div style="font-size: 14px; font-weight: bold; color: #4338CA;">{jogo['Home']} vs {jogo['Away']}</div>
            <div style="margin-top:10px;"><span class="value-badge">{jogo['💡 Sugestão Value']}</span></div>
            <div style="margin-top:10px;">📊 xG: {jogo['Expected Goals']} | 🎯 BTTS: {jogo['BTTS %']}% | Placar: {jogo['Placar Provável']}</div>
            <div style="display:flex; gap:10px; margin-top:10px;">
                <div class="odd-box-back">Casa: {jogo['Home Win %']}%</div>
                <div class="odd-box-back">Fora: {jogo['Away Win %']}%</div>
                <div class="odd-box-goals">Over 2.5: {jogo['Over 2.5 %']}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Nenhum dado retornado.")
