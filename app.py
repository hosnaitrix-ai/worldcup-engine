import sys
import time
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

# --- CONFIGURAÇÃO ---
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

st.set_page_config(page_title="LiveScanner Pro", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .match-box { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; }
    .value-badge { background: #4338CA; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
    .metric-row { display: flex; gap: 20px; margin-top: 10px; font-size: 0.9rem; color: #475569; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 LiveScanner Pro - Análise de Futebol")

# =========================================================
# 🧠 DICIONÁRIO DE LIGAS (NOVO)
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

# --- PESO TEMPORAL ---
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

# --- FORÇA DO TIME (MELHORADA) ---
def forca_time(team, side, data_ref, liga_jogo, l_home, l_away, df_hist):

    jogos_liga = df_hist[(df_hist["Date"] < data_ref) & (df_hist["League"] == liga_jogo)]
    t = jogos_liga[jogos_liga["Home"] == team] if side == "home" else jogos_liga[jogos_liga["Away"] == team]

    if len(t) < 3:
        t = jogos_liga.copy()

    if len(t) == 0:
        return 1.0, 1.0

    t = t.copy()
    t["peso"] = peso_temporal(t["Date"], data_ref)

    atk_col = "GOLS_HOME" if side == "home" else "GOLS_AWAY"
    def_col = "GOLS_AWAY" if side == "home" else "GOLS_HOME"

    atk = np.average(t[atk_col], weights=t["peso"])
    defe = np.average(t[def_col], weights=t["peso"])

    fator = min(len(t) / 10, 1)

    ataque = fator * (atk / l_home if side == "home" else atk / l_away) + (1 - fator)
    defesa = fator * (defe / l_away if side == "home" else defe / l_home) + (1 - fator)

    return np.clip(ataque, 0.5, 2.2), np.clip(defesa, 0.5, 2.2)

# --- DIXON COLES ---
def dixon_coles(lh, la, rho=-0.1):
    p_h = poisson.pmf(np.arange(11), lh)
    p_a = poisson.pmf(np.arange(11), la)
    m = np.outer(p_h, p_a)

    m[0,0] *= (1 - lh * la * rho)
    m[0,1] *= (1 + lh * rho)
    m[1,0] *= (1 + la * rho)
    m[1,1] *= (1 - rho)

    return m / m.sum()

# --- VALUE DETECTOR ---
def detectar_melhor_valor(hw, d, aw, o15, o25, btts, xg, home, away):

    if hw > 65:
        return f"🔥 Vitória {home}"

    if aw > 48:
        return f"🚀 Vitória {away}"

    if o25 > 60 and xg > 2.4:
        return "⚽ Over 2.5"

    if btts > 60:
        return "🎯 BTTS SIM"

    if (aw + d) > 70:
        return f"🛡️ Dupla Chance {away}/Empate"

    if o15 > 80:
        return "🛡️ Over 1.5"

    return "⚖️ Sem Value"

# --- DADOS ---
df = carregar_dados_online()

df_future = df[df["GOLS_HOME"].isna()].copy()
df_hist = df[df["GOLS_HOME"].notna()].copy()

saida = []

# =========================================================
# 🔁 LOOP PRINCIPAL
# =========================================================
for _, r in df_future.iterrows():

    liga_info = LIGAS_MAPA.get(
        r["League"],
        {"base_home": 1.4, "base_away": 1.1}
    )

    base_home = liga_info["base_home"]
    base_away = liga_info["base_away"]

    l_h_m = df_hist[df_hist["League"] == r["League"]]["GOLS_HOME"].mean()
    l_a_m = df_hist[df_hist["League"] == r["League"]]["GOLS_AWAY"].mean()

    if pd.isna(l_h_m):
        l_h_m, l_a_m = base_home, base_away

    ah, dh = forca_time(r["Home"], "home", r["Date"], r["League"], l_h_m, l_a_m, df_hist)
    aa, da = forca_time(r["Away"], "away", r["Date"], r["League"], l_h_m, l_a_m, df_hist)

    # 🔥 xG com normalização por liga
    xg_h = (ah * da * base_home) * 0.7 + base_home * 0.3
    xg_a = (aa * dh * base_away) * 0.7 + base_away * 0.3

    xg_h = np.clip(xg_h, 0.2, 2.6)
    xg_a = np.clip(xg_a, 0.2, 2.4)

    p = dixon_coles(xg_h, xg_a)

    hw = np.sum(np.tril(p, -1)) * 100
    d = np.sum(np.diag(p)) * 100
    aw = np.sum(np.triu(p, 1)) * 100

    gols = np.array([
        np.sum([p[i, j] for i in range(11) for j in range(11) if i + j == k])
        for k in range(11)
    ])

    o15 = (1 - gols[0] - gols[1]) * 100
    o25 = (1 - np.sum(gols[:3])) * 100

    btts = (1 - p[0, :].sum() - p[:, 0].sum() + p[0, 0]) * 100

    val = detectar_melhor_valor(hw, d, aw, o15, o25, btts, xg_h + xg_a, r["Home"], r["Away"])

    saida.append({
        "Home": r["Home"],
        "Away": r["Away"],
        "Value": val,
        "xG": round(xg_h + xg_a, 2),
        "BTTS %": round(btts, 1)
    })

# --- UI ---
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
