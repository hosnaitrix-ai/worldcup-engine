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
    page_title="LiveScanner Pro - ESPN Trading Engine",
    page_icon="⚡",
    layout="wide"
)

st.title("📊 LIVE SCANNER PRO | ESPN TRADING ENGINE")

# =========================================================
# LIGAS MAPA (REGRAS DO MODELO)
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
# ESPN DATA ENGINE (FILTRADO POR LIGAS DO MAPA)
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

df_hist = df[df["GOLS_HOME"].notna()]
df_future = df[df["GOLS_HOME"].isna()]

# =========================================================
# FUNÇÕES MODELO
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga, l_home, l_away):

    df_liga = df_hist[df_hist["League"] == liga]
    t = df_liga[df_liga["Home"] == team] if side == "home" else df_liga[df_liga["Away"] == team]

    if len(t) < 3:
        t = df_liga

    if len(t) == 0:
        return 1.0, 1.0

    t = t.copy()
    t["peso"] = peso_temporal(t["Date"], data_ref)

    atk_col = "GOLS_HOME" if side == "home" else "GOLS_AWAY"
    def_col = "GOLS_AWAY" if side == "home" else "GOLS_HOME"

    atk = np.average(t[atk_col], weights=t["peso"])
    defe = np.average(t[def_col], weights=t["peso"])

    fator = min(len(t) / 8, 1)

    ataque = fator * (atk / l_home if side == "home" else atk / l_away) + (1 - fator)
    defesa = fator * (defe / l_away if side == "home" else defe / l_home) + (1 - fator)

    return np.clip(ataque, 0.5, 2.2), np.clip(defesa, 0.5, 2.2)

def dixon_coles(lh, la, rho=-0.1):
    p_h = poisson.pmf(np.arange(11), lh)
    p_a = poisson.pmf(np.arange(11), la)
    m = np.outer(p_h, p_a)

    m[0,0] *= (1 - lh * la * rho)
    m[0,1] *= (1 + lh * rho)
    m[1,0] *= (1 + la * rho)
    m[1,1] *= (1 - rho)

    return m / m.sum()

# =========================================================
# VALUE ENGINE
# =========================================================
def detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg, home, away):

    if hw > 62:
        return f"🔥 Mandante Forte: {home}"

    if aw > 45:
        return f"🚀 Visitante Forte: {away}"

    if o25 > 58 and xg > 2.5:
        return "⚽ Over 2.5 Value"

    if d > 30 and u35 > 78:
        return "🔒 Jogo Travado"

    if (aw + d) > 65:
        return f"🛡️ Dupla Chance {away}/Empate"

    return "⚖️ Sem Valor"

# =========================================================
# PIPELINE
# =========================================================
saida = []

for _, r in df_future.iterrows():

    liga = r["League"]
    base = LIGAS_MAPA[liga]

    l_h = df_hist[df_hist["League"] == liga]["GOLS_HOME"].mean()
    l_a = df_hist[df_hist["League"] == liga]["GOLS_AWAY"].mean()

    if pd.isna(l_h):
        l_h, l_a = base["base_home"], base["base_away"]

    ah, dh = forca_time(r["Home"], "home", r["Date"], liga, l_h, l_a)
    aa, da = forca_time(r["Away"], "away", r["Date"], liga, l_h, l_a)

    # xG CALIBRADO
    xg_h = (ah * da * base["base_home"]) * 0.7 + base["base_home"] * 0.3
    xg_a = (aa * dh * base["base_away"]) * 0.7 + base["base_away"] * 0.3

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
# UI SIMPLES + TRADING
# =========================================================
st.subheader("📊 Scanner de Jogos (ESPN + Trading Model)")

if saida:
    for j in saida:
        st.markdown(f"""
        <div style="padding:15px;border-radius:10px;border:1px solid #ddd;margin-bottom:10px">
            <b>{j['Home']} vs {j['Away']}</b><br>
            <small>{j['League']}</small><br><br>

            <b>{j['Value']}</b><br><br>

            📊 xG: {j['xG']}<br>
            🏠 {j['Home%']}% | 🤝 {j['Draw%']}% | 🚀 {j['Away%']}%<br>
            ⚽ Over 2.5: {j['Over2.5%']}%
        </div>
        """, unsafe_allow_html=True)
else:
    st.warning("Nenhum jogo encontrado na ESPN.")
