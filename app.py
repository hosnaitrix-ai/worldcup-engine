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
# CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL TRADING
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
    .match-header { font-size: 12px; color: #64748B; font-weight: 600; text-transform: uppercase; margin-bottom: 0.8rem; }
    .league-badge { background: #F1F5F9; color: #4338CA; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .team-name { font-size: 1.25rem; font-weight: 700; color: #1E293B; }
    .vs-badge { font-size: 10px; background: #F1F5F9; color: #64748B; padding: 2px 8px; border-radius: 4px; margin: 0 10px; font-weight: bold; }
    
    .odd-box-back { background: #E0F2FE; border: 1px solid #7DD3FC; color: #0369A1; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; }
    .odd-box-lay { background: #FCE7F3; border: 1px solid #FBCFE8; color: #B91C1C; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; }
    .odd-box-goals { background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; }
    
    .value-badge { background: #4338CA; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 13px; }
    .value-report-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }
    .report-topic { font-size: 12px; font-weight: 700; color: #4338CA; margin-bottom: 4px; }
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
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
}

# =========================================================
# DATA ENGINE (CORRIGIDO)
# =========================================================
@st.cache_data(ttl=300)
def carregar_dados_online():
    todos_jogos = []

    for nome_liga, config in LIGAS_MAPA.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard"

        try:
            r = requests.get(url, timeout=6)
            if r.status_code != 200:
                continue

            data = r.json()

            for event in data.get("events", []):
                comp = event["competitions"][0]
                home_node = comp["competitors"][0]
                away_node = comp["competitors"][1]

                h_team = home_node["team"]["displayName"]
                a_team = away_node["team"]["displayName"]

                status = event["status"]["type"]["name"]

                date_utc = pd.to_datetime(event["date"], utc=True)
                date_local = date_utc.tz_convert("America/Sao_Paulo")
                date_raw = date_local.replace(tzinfo=None)

                h_score = np.nan
                a_score = np.nan

                if status in ["STATUS_FULL_TIME", "STATUS_FINAL"]:
                    h_score = int(home_node["score"])
                    a_score = int(away_node["score"])

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

        except Exception:
            continue

    df = pd.DataFrame(todos_jogos)

    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]

    return df


df = carregar_dados_online()

if df.empty:
    st.error("Sem dados da API.")
    st.stop()

# =========================================================
# SEPARAÇÃO CORRIGIDA
# =========================================================
hoje = pd.Timestamp.now().normalize()

df_hist = df[df["GOLS_HOME"].notna()].copy()
df_future = df[df["GOLS_HOME"].isna()].copy()

# =========================================================
# MODELO SIMPLIFICADO
# =========================================================
def dixon_coles(lh, la, max_g=10):
    p_h = poisson.pmf(range(max_g+1), lh)
    p_a = poisson.pmf(range(max_g+1), la)
    return np.outer(p_h, p_a)

# =========================================================
# SCANNER
# =========================================================
st.subheader("📊 Scanner")

saida = []

if not df_future.empty:

    for _, r in df_future.iterrows():

        home = r["Home"]
        away = r["Away"]
        liga = r["League"]

        xg_h = 1.4
        xg_a = 1.1

        p = dixon_coles(xg_h, xg_a)

        home_win = np.sum(np.tril(p, -1)) * 100
        draw = np.sum(np.diag(p)) * 100
        away_win = np.sum(np.triu(p, 1)) * 100

        saida.append({
            "Date": r["DateStr"],
            "Time": r["Time"],
            "Home": home,
            "Away": away,
            "League": liga,
            "Home Win %": round(home_win, 1),
            "Draw %": round(draw, 1),
            "Away Win %": round(away_win, 1),
        })

if saida:

    df_proj = pd.DataFrame(saida)

    data_sel = st.selectbox("Filtrar data", df_proj["Date"].unique())

    df_filtrado = df_proj[df_proj["Date"] == data_sel]

    for _, j in df_filtrado.iterrows():

        st.markdown(f"""
        <div class="match-box">
            <div class="match-header">
                {j['League']} - {j['Date']} {j['Time']}
            </div>

            <div>
                <span class="team-name">{j['Home']}</span>
                <span class="vs-badge">VS</span>
                <span class="team-name">{j['Away']}</span>
            </div>

            <br>

            <div style="display:flex; gap:10px;">
                <div class="odd-box-back">Casa {j['Home Win %']}%</div>
                <div class="odd-box-lay">Empate {j['Draw %']}%</div>
                <div class="odd-box-back">Fora {j['Away Win %']}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.info("Nenhum jogo futuro encontrado.")
