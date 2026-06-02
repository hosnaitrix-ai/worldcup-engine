import sys
import time
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

# --- CONFIGURAÇÃO DE AMBIENTE ---
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

st.set_page_config(page_title="LiveScanner Pro", layout="wide")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .match-box { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .value-badge { background: #4338CA; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
    .metric-row { display: flex; gap: 20px; margin-top: 10px; font-size: 0.9rem; color: #475569; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 LiveScanner Pro - Análise de Futebol")

# --- FUNÇÕES MATEMÁTICAS ---
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga_jogo, l_home, l_away, df_hist):
    jogos = df_hist[(df_hist["Date"] < data_ref) & (df_hist["League"] == liga_jogo)].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    if len(t) < 3: return 1.0, 1.0
    
    t.loc[:, "peso"] = peso_temporal(t["Date"], data_ref)
    atk = np.average(t["GOLS_HOME" if side == "home" else "GOLS_AWAY"], weights=t["peso"])
    defe = np.average(t["GOLS_AWAY" if side == "home" else "GOLS_HOME"], weights=t["peso"])
    
    ataque = (atk / (l_home if side == "home" else l_away))
    defesa = (defe / (l_away if side == "home" else l_home))
    return np.clip(ataque, 0.5, 2.2), np.clip(defesa, 0.5, 2.2)

def dixon_coles(lh, la, rho=-0.1):
    p_h = poisson.pmf(np.arange(11), lh)
    p_a = poisson.pmf(np.arange(11), la)
    m = np.outer(p_h, p_a)
    m[0,0]*=(1-lh*la*rho); m[0,1]*=(1+lh*rho); m[1,0]*=(1+la*rho); m[1,1]*=(1-rho)
    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, btts, xg, home, away):
    if hw > 62: return f"🔥 Vitória {home}"
    if aw > 45: return f"🚀 Vitória {away}"
    if o25 > 58 and xg > 2.7: return "⚽ Over 2.5"
    if btts > 58: return "🎯 BTTS SIM"
    return "⚖️ Sem Value"

# --- PROCESSAMENTO ---
# IMPORTANTE: A função 'carregar_dados_online()' deve estar definida no seu código
df = carregar_dados_online() 
df_future = df[df["GOLS_HOME"].isna()].copy()
df_hist = df[df["GOLS_HOME"].notna()].copy()

saida = []
for _, r in df_future.iterrows():
    # Médias da Liga
    l_h_m = df_hist[df_hist["League"] == r["League"]]["GOLS_HOME"].mean()
    l_a_m = df_hist[df_hist["League"] == r["League"]]["GOLS_AWAY"].mean()
    if pd.isna(l_h_m): l_h_m, l_a_m = 1.4, 1.1
    
    ah, dh = forca_time(r["Home"], "home", r["Date"], r["League"], l_h_m, l_a_m, df_hist)
    aa, da = forca_time(r["Away"], "away", r["Date"], r["League"], l_h_m, l_a_m, df_hist)
    
    xg_h = np.clip((ah * da * l_h_m), 0.2, 2.6)
    xg_a = np.clip((aa * dh * l_a_m), 0.2, 2.4)
    
    p = dixon_coles(xg_h, xg_a)
    hw, d, aw = np.sum(np.tril(p, -1))*100, np.sum(np.diag(p))*100, np.sum(np.triu(p, 1))*100
    gols = np.array([np.sum([p[i, j] for i in range(11) for j in range(11) if i + j == k]) for k in range(11)])
    o15, o25 = (1-gols[0]-gols[1])*100, (1-np.sum(gols[:3]))*100
    btts = (1 - p[0, :].sum() - p[:, 0].sum() + p[0, 0]) * 100
    
    val = detectar_melhor_valor(hw, d, aw, o15, o25, btts, xg_h+xg_a, r["Home"], r["Away"])
    
    saida.append({
        "Home": r["Home"], "Away": r["Away"], "Value": val, 
        "xG": round(xg_h+xg_a, 2), "BTTS %": round(btts, 1)
    })

# --- INTERFACE ---
if saida:
    for j in saida:
        st.markdown(f"""
        <div class="match-box">
            <b>{j['Home']} vs {j['Away']}</b><br>
            <span class="value-badge">{j['Value']}</span>
            <div class="metric-row">
                <span>📊 xG Total: {j['xG']}</span>
                <span>🎯 BTTS: {j['BTTS %']}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Nenhum jogo encontrado para análise.")
