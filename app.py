import sys
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
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="LiveScanner Pro - Multi-Liga Online",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""<style>
.block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
h1 { font-weight: 900 !important; color: #0F172A; }
.metric-card { background-color: #0F172A; padding: 1.2rem; border-radius: 8px; color: white; }
.match-box { background: #fff; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.2rem; }
.value-badge { background: #4338CA; color: white; padding: 6px 10px; border-radius: 6px; }
</style>""", unsafe_allow_html=True)

st.title("📊 LIVE SCANNER PRO | ESPN TRADING ENGINE")

# =========================================================
# LIGAS (BASE OFICIAL)
# =========================================================
LIGAS_MAPA = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Brasileirão - Série C": {"slug": "bra.3", "base_home": 1.30, "base_away": 0.90},
    "Equador - LigaPro": {"slug": "ecu.1", "base_home": 1.60, "base_away": 1.10},
    "Chile - Primera División": {"slug": "chi.1", "base_home": 1.50, "base_away": 1.12},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Suécia - Superettan": {"slug": "swe.2", "base_home": 1.55, "base_away": 1.20},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
}

# =========================================================
# API ESPN
# =========================================================
@st.cache_data(ttl=300)
def carregar_dados_online():
    jogos = []

    for liga, cfg in LIGAS_MAPA.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{cfg['slug']}/scoreboard"

        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue

            data = r.json()

            for ev in data.get("events", []):
                comp = ev["competitions"][0]
                home = comp["competitors"][0]
                away = comp["competitors"][1]

                home_team = home["team"]["displayName"]
                away_team = away["team"]["displayName"]

                home_score = int(home["score"]) if home.get("score") else np.nan
                away_score = int(away["score"]) if away.get("score") else np.nan

                jogos.append({
                    "League": liga,
                    "Date": pd.to_datetime(ev["date"]).tz_localize(None),
                    "Home": home_team,
                    "Away": away_team,
                    "GOLS_HOME": home_score,
                    "GOLS_AWAY": away_score
                })

        except:
            continue

    df = pd.DataFrame(jogos)

    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]

    return df


df = carregar_dados_online()

if df.empty:
    st.error("Sem dados da ESPN")
    st.stop()

df_hist = df.dropna().copy()
df_future = df[df["GOLS_HOME"].isna()].copy()

hoje = pd.Timestamp.now().floor("D")

# =========================================================
# PESO TEMPORAL
# =========================================================
def peso_temporal(data_jogo, data_ref):
    dias = (data_ref - data_jogo).days
    return np.exp(-0.006 * dias)

# =========================================================
# FORÇA DE TIME (AJUSTADA)
# =========================================================
def forca_time(team, side, data_ref, liga, lh, la):

    jogos = df_hist[(df_hist["League"] == liga) & (df_hist["Date"] < data_ref)]

    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]

    if len(t) < 3:
        t = jogos

    if len(t) == 0:
        return 1.0, 1.0

    t = t.copy()
    t["peso"] = peso_temporal(t["Date"], data_ref)

    if side == "home":
        atk = np.average(t["GOLS_HOME"], weights=t["peso"])
        def_ = np.average(t["GOLS_AWAY"], weights=t["peso"])
    else:
        atk = np.average(t["GOLS_AWAY"], weights=t["peso"])
        def_ = np.average(t["GOLS_HOME"], weights=t["peso"])

    ataque = min(max(atk / lh, 0.6), 1.8)
    defesa = min(max(def_ / la, 0.6), 1.8)

    return ataque, defesa

# =========================================================
# POISSON
# =========================================================
def dixon_coles(lh, la, max_g=8):
    p_h = poisson.pmf(range(max_g), lh)
    p_a = poisson.pmf(range(max_g), la)
    m = np.outer(p_h, p_a)
    return m / m.sum()

# =========================================================
# VALUE DETECTOR
# =========================================================
def detectar_melhor_valor(hw, d, aw, o15, o25, u35, btts, xg, home, away):

    if hw > 62:
        return f"🔥 {home} vence"

    if aw > 55:
        return f"🚀 {away} vence"

    if btts > 60:
        return "🎯 BTTS SIM"

    if o25 > 58 and xg > 2.2:
        return "⚽ Over 2.5"

    if d > 30:
        return "🤝 Empate forte"

    if o15 > 80:
        return "🛡️ Over 1.5"

    return "⚖️ Sem valor"

# =========================================================
# BTTS + PLACAR
# =========================================================
def extras(p):

    btts = (1 - p[0, :].sum() - p[:, 0].sum() + p[0, 0]) * 100

    best = np.unravel_index(np.argmax(p), p.shape)
    score = f"{best[0]}x{best[1]}"

    return btts, score

# =========================================================
# SCANNER
# =========================================================
st.subheader("📊 Scanner ESPN")

saida = []

for _, r in df_future.iterrows():

    liga = r["League"]

    lh = LIGAS_MAPA[liga]["base_home"]
    la = LIGAS_MAPA[liga]["base_away"]

    ah, dh = forca_time(r["Home"], "home", r["Date"], liga, lh, la)
    aa, da = forca_time(r["Away"], "away", r["Date"], liga, lh, la)

    xg_h = (ah * da * lh) * 0.7 + lh * 0.3
    xg_a = (aa * dh * la) * 0.7 + la * 0.3

    xg_h = np.clip(xg_h, 0.3, 2.4)
    xg_a = np.clip(xg_a, 0.3, 2.4)

    p = dixon_coles(xg_h, xg_a)

    home = np.sum(np.tril(p, -1)) * 100
    draw = np.sum(np.diag(p)) * 100
    away = np.sum(np.triu(p, 1)) * 100

    total = xg_h + xg_a

    gols = np.array([np.sum([p[i, j] for i in range(8) for j in range(8) if i+j == k]) for k in range(15)])

    o15 = (1 - gols[0] - gols[1]) * 100
    o25 = (1 - np.sum(gols[:3])) * 100
    u35 = np.sum(gols[:4]) * 100

    btts, score = extras(p)

    value = detectar_melhor_valor(home, draw, away, o15, o25, u35, btts, total, r["Home"], r["Away"])

    saida.append({
        "Home": r["Home"],
        "Away": r["Away"],
        "League": liga,
        "xG": round(total, 2),
        "1": round(home, 1),
        "X": round(draw, 1),
        "2": round(away, 1),
        "Over2.5": round(o25, 1),
        "BTTS": round(btts, 1),
        "Score": score,
        "Value": value
    })

df_out = pd.DataFrame(saida)

st.dataframe(df_out, use_container_width=True)
