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
# CONFIGURAÇÃO DA PÁGINA
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
    
    .metric-card { background-color: #0F172A; padding: 1.2rem; border-radius: 8px; border-left: 4px solid #10B981; color: white; }
    .metric-title { font-size: 11px; text-transform: uppercase; color: #94A3B8; letter-spacing: 1px; font-weight: bold; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #10B981; margin-top: 2px; }
    
    .match-box { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; }
    .league-badge { background: #F1F5F9; color: #4338CA; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .team-name { font-size: 1.25rem; font-weight: 700; color: #1E293B; }
    .vs-badge { font-size: 10px; background: #F1F5F9; color: #64748B; padding: 2px 8px; border-radius: 4px; margin: 0 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 ANÁLISE DE FUTEBOL - By Freed Cesar")
st.markdown("---")

# =========================================================
# LIGAS
# =========================================================
LIGAS_MAPA = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Equador - LigaPro": {"slug": "ecu.1", "base_home": 1.60, "base_away": 1.10},
    "Chile - Primera División": {"slug": "chi.1", "base_home": 1.50, "base_away": 1.12},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
}

# =========================================================
# API ESPN
# =========================================================
@st.cache_data(ttl=300)
def carregar_dados_online():
    todos_jogos = []

    for nome_liga, config in LIGAS_MAPA.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard"

        try:
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue

            data = r.json()

            for event in data.get("events", []):

                status = event["status"]["type"]["name"]

                # ✅ CORREÇÃO PRINCIPAL: sem offset de -3h
                date_raw = pd.to_datetime(event["date"], utc=True).tz_convert(None)

                comp = event["competitions"][0]
                home = comp["competitors"][0]
                away = comp["competitors"][1]

                h_team = home["team"]["displayName"]
                a_team = away["team"]["displayName"]

                h_score = np.nan
                a_score = np.nan

                if status in ["STATUS_FINAL", "STATUS_FULL_TIME"]:
                    h_score = int(home["score"])
                    a_score = int(away["score"])

                todos_jogos.append({
                    "League": nome_liga,
                    "Date": date_raw,
                    "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "Time": date_raw.strftime("%H:%M"),
                    "Home": h_team,
                    "Away": a_team,
                    "GOLS_HOME": h_score,
                    "GOLS_AWAY": a_score,
                })

        except:
            continue

    df = pd.DataFrame(todos_jogos)

    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]

    return df


df = carregar_dados_online()

if df.empty:
    st.error("Nenhum dado retornado da ESPN")
    st.stop()

# =========================================================
# ✅ CORREÇÃO DE DATA (CRÍTICO)
# =========================================================
hoje = pd.Timestamp.now().normalize()

df_hist = df[df["GOLS_HOME"].notna()].copy()

df_future = df[
    df["GOLS_HOME"].isna()
].copy()

df_future = df_future[df_future["Date"].dt.normalize() >= hoje]

# =========================================================
# FUNÇÕES
# =========================================================
def dixon_coles(lh, la, max_g=8):
    ph = poisson.pmf(range(max_g+1), lh)
    pa = poisson.pmf(range(max_g+1), la)
    m = np.outer(ph, pa)
    return m / m.sum()


def forca_time(team, side):
    if df_hist.empty:
        return 1.0, 1.0

    jogos = df_hist

    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]

    if len(t) == 0:
        return 1.0, 1.0

    atk = np.nanmean(t["GOLS_HOME"] if side == "home" else t["GOLS_AWAY"])
    def_ = np.nanmean(t["GOLS_AWAY"] if side == "home" else t["GOLS_HOME"])

    return atk or 1.2, def_ or 1.2


# =========================================================
# PROJEÇÃO
# =========================================================
st.subheader("📊 Scanner de Jogos")

saida = []

if not df_future.empty:

    for _, r in df_future.iterrows():

        home = r["Home"]
        away = r["Away"]

        ah, ad = forca_time(home, "home")
        aa, ad2 = forca_time(away, "away")

        xg_h = max(0.8, ah * 1.3)
        xg_a = max(0.8, aa * 1.1)

        p = dixon_coles(xg_h, xg_a)

        home_win = np.sum(np.tril(p, -1)) * 100
        draw = np.sum(np.diag(p)) * 100
        away_win = np.sum(np.triu(p, 1)) * 100

        over25 = (1 - np.sum(p[:3, :3])) * 100

        saida.append({
            "Date": r["DateStr"],
            "Home": home,
            "Away": away,
            "Home Win %": round(home_win, 1),
            "Draw %": round(draw, 1),
            "Away Win %": round(away_win, 1),
            "Over 2.5 %": round(over25, 1),
        })

    df_proj = pd.DataFrame(saida)

    # =====================================================
    # OUTPUT SEM QUEBRAR
    # =====================================================
    for _, j in df_proj.iterrows():
        st.markdown(f"""
        <div class="match-box">
            <div class="league-badge">{j['Date']}</div>
            <h3>{j['Home']} vs {j['Away']}</h3>

            <p>
            🏠 Home: {j['Home Win %']}% | 🤝 {j['Draw %']}% | 🚀 {j['Away Win %']}%
            </p>

            <p><b>Over 2.5:</b> {j['Over 2.5 %']}%</p>
        </div>
        """, unsafe_allow_html=True)

else:
    st.warning("⚠️ Nenhum jogo futuro encontrado na ESPN agora.")
