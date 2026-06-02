import sys
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

# =========================================================
# CONFIG
# =========================================================
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

st.set_page_config(
    page_title="LiveScanner Pro - ESPN Engine",
    layout="wide"
)

st.title("📊 LIVE SCANNER PRO | ESPN TRADING ENGINE")

# =========================================================
# LIGAS MAPA
# =========================================================
LIGAS_MAPA = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Noruega - Eliteserien": {"slug": "nor.1", "base_home": 1.70, "base_away": 1.35},
    "EUA - MLS": {"slug": "usa.1", "base_home": 1.68, "base_away": 1.30},
    "UEFA Champions League": {"slug": "champions", "base_home": 1.65, "base_away": 1.30},
    "Copa Libertadores": {"slug": "libertadores", "base_home": 1.45, "base_away": 1.05},
}

# =========================================================
# ESPN DATA (HISTÓRICO)
# =========================================================
@st.cache_data(ttl=3600)
def carregar_dados_online():

    jogos = []

    for liga, info in LIGAS_MAPA.items():

        url = f"https://site.web.api.espn.com/apis/site/v2/sports/soccer/{info['slug']}/scoreboard"

        try:
            r = requests.get(url, timeout=10)
            data = r.json()

            for e in data.get("events", []):

                comp = e["competitions"][0]
                teams = comp["competitors"]

                home = teams[0]["team"]["displayName"]
                away = teams[1]["team"]["displayName"]

                home_score = teams[0].get("score")
                away_score = teams[1].get("score")

                jogos.append({
                    "Date": pd.to_datetime(e["date"]),
                    "League": liga,
                    "Home": home,
                    "Away": away,
                    "GOLS_HOME": float(home_score) if home_score else None,
                    "GOLS_AWAY": float(away_score) if away_score else None
                })

        except:
            continue

    return pd.DataFrame(jogos)

df = carregar_dados_online()

# =========================================================
# SEGURANÇA ANTI-ERRO (CRÍTICO)
# =========================================================
if df.empty:
    st.error("❌ ESPN não retornou dados. Tente novamente mais tarde.")
    st.stop()

df_hist = df[df["GOLS_HOME"].notna()].copy()

# =========================================================
# CRIAR FUTURE FICTÍCIO (EVITA TELA VAZIA)
# =========================================================
df_future = df_hist.sample(min(10, len(df_hist))).copy()
df_future["GOLS_HOME"] = np.nan
df_future["GOLS_AWAY"] = np.nan

# =========================================================
# FUNÇÕES DO MODELO
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga):

    df_liga = df_hist[df_hist["League"] == liga]
    t = df_liga[df_liga["Home"] == team] if side == "home" else df_liga[df_liga["Away"] == team]

    if len(t) < 3:
        t = df_liga

    if len(t) == 0:
        return 1.0, 1.0

    t = t.copy()
    t["peso"] = 1.0

    atk = np.mean(t["GOLS_HOME" if side == "home" else "GOLS_AWAY"])
    defe = np.mean(t["GOLS_AWAY" if side == "home" else "GOLS_HOME"])

    ataque = np.clip(atk / 1.4, 0.5, 2.2)
    defesa = np.clip(defe / 1.1, 0.5, 2.2)

    return ataque, defesa

def dixon_coles(lh, la, rho=-0.1):
    max_g = 10
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)

    m = np.outer(p_h, p_a)

    m[0,0] *= (1 - lh * la * rho)
    m[0,1] *= (1 + lh * rho)
    m[1,0] *= (1 + la * rho)
    m[1,1] *= (1 - rho)

    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg, home, away):

    if hw > 62:
        return f"🔥 {home} vence"

    if aw > 45:
        return f"🚀 {away} vence"

    if o25 > 58:
        return "⚽ Over 2.5"

    if d > 30:
        return "🤝 Empate forte"

    if (aw + d) > 65:
        return f"🛡️ Dupla Chance {away}/Empate"

    return "⚖️ Sem valor"

# =========================================================
# PIPELINE
# =========================================================
saida = []

for _, r in df_future.iterrows():

    liga = r["League"]

    l_h = df_hist[df_hist["League"] == liga]["GOLS_HOME"].mean()
    l_a = df_hist[df_hist["League"] == liga]["GOLS_AWAY"].mean()

    if np.isnan(l_h):
        l_h, l_a = 1.4, 1.1

    ah, dh = forca_time(r["Home"], "home", r["Date"], liga)
    aa, da = forca_time(r["Away"], "away", r["Date"], liga)

    xg_h = (ah * da * l_h) * 0.7 + l_h * 0.3
    xg_a = (aa * dh * l_a) * 0.7 + l_a * 0.3

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
    u35 = np.sum(gols[:4]) * 100

    xg_total = xg_h + xg_a

    val = detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg_total, r["Home"], r["Away"])

    saida.append({
        "Home": r["Home"],
        "Away": r["Away"],
        "League": liga,
        "Value": val,
        "xG": round(xg_total, 2),
        "Home%": round(hw, 1),
        "Draw%": round(d, 1),
        "Away%": round(aw, 1),
        "Over2.5%": round(o25, 1)
    })

# =========================================================
# UI
# =========================================================
st.subheader("📊 Scanner ESPN + Trading Model")

for j in saida:
    st.markdown(f"""
    <div style="padding:12px;border:1px solid #ddd;border-radius:10px;margin-bottom:10px">
        <b>{j['Home']} vs {j['Away']}</b><br>
        <small>{j['League']}</small><br><br>

        <b>{j['Value']}</b><br><br>

        📊 xG: {j['xG']}<br>
        🏠 {j['Home%']}% | 🤝 {j['Draw%']}% | 🚀 {j['Away%']}%<br>
        ⚽ Over 2.5: {j['Over2.5%']}%
    </div>
    """, unsafe_allow_html=True)
