import sys
import time
import random
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
st.markdown("---")

# =========================================================
# LIGAS
# =========================================================
LIGAS_MAPA = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Brasileirão - Feminino": {"slug": "bra.women.1", "base_home": 1.58, "base_away": 1.18},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
    "Finlândia - Veikkausliiga": {"slug": "fin.1", "base_home": 1.48, "base_away": 1.18},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Noruega - Eliteserien": {"slug": "nor.1", "base_home": 1.70, "base_away": 1.35},
    "EUA - MLS": {"slug": "usa.1", "base_home": 1.68, "base_away": 1.30},
    "UEFA Champions League": {"slug": "champions", "base_home": 1.65, "base_away": 1.30},
}

# =========================================================
# DADOS ONLINE
# =========================================================
@st.cache_data(ttl=300)
def carregar_dados_online():
    todos_jogos = []
    hoje = pd.Timestamp.now().normalize()

    # 🔥 12 DIAS À FRENTE
    datas_alvo = [hoje + pd.Timedelta(days=i) for i in range(0, 13)]

    for nome_liga, config in LIGAS_MAPA.items():

        # 🔥 DELAY ANTI-BLOQUEIO
        time.sleep(random.uniform(0.6, 1.4))

        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard"

        try:
            response = requests.get(url, timeout=8)
            if response.status_code != 200:
                continue

            data = response.json()

            for event in data.get("events", []):

                comp = event["competitions"][0]
                home_node = comp["competitors"][0]
                away_node = comp["competitors"][1]

                h_team = home_node["team"]["displayName"].strip()
                a_team = away_node["team"]["displayName"].strip()

                if not h_team or not a_team:
                    continue

                status_type = event["status"]["type"]["name"]

                date_utc = pd.to_datetime(event["date"], utc=True)
                date_local = date_utc.tz_convert("America/Sao_Paulo")
                date_raw = date_local.replace(tzinfo=None)

                h_score = np.nan
                a_score = np.nan

                if status_type in ["STATUS_FULL_TIME", "STATUS_FINAL"]:
                    h_score = int(home_node["score"])
                    a_score = int(away_node["score"])

                uid = f"{nome_liga}_{date_raw}_{h_team}_{a_team}".replace(" ", "_")

                todos_jogos.append({
                    "UID": uid,
                    "League": nome_liga,
                    "Date": date_raw,
                    "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "Time": date_raw.strftime("%H:%M"),
                    "Home": h_team,
                    "Away": a_team,
                    "GOLS_HOME": h_score,
                    "GOLS_AWAY": a_score,
                    "Score": f"{h_score}–{a_score}" if not np.isnan(h_score) else "vs",
                    "Status": status_type
                })

        except Exception as e:
            print(f"Erro liga {nome_liga}: {e}")
            continue

    df = pd.DataFrame(todos_jogos)

    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]
        df = df.drop_duplicates(subset=["UID"])

    return df


df = carregar_dados_online()

if df.empty:
    st.error("Nenhum dado encontrado.")
    st.stop()

# =========================================================
# SEPARAÇÃO
# =========================================================
df_future = df[df["GOLS_HOME"].isna()].copy()
df_hist = df[df["GOLS_HOME"].notna()].copy()

# =========================================================
# MODELO
# =========================================================
def dixon_coles(lh, la, rho=-0.1, max_g=10):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)

    m[0, 0] *= (1 - lh * la * rho)
    m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho)
    m[1, 1] *= (1 - rho)

    return m / m.sum()

def forca_time(team, side, data_ref, liga):
    jogos = df_hist[df_hist["League"] == liga]
    if jogos.empty:
        return 1.0, 1.0

    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    if t.empty:
        return 1.0, 1.0

    if side == "home":
        return 1.2, 1.1
    return 1.0, 1.0

# =========================================================
# SCANNER
# =========================================================
saida = []

for _, r in df_future.iterrows():

    home = r["Home"]
    away = r["Away"]
    liga = r["League"]

    ah, dh = forca_time(home, "home", r["Date"], liga)
    aa, da = forca_time(away, "away", r["Date"], liga)

    xg_h = np.clip(ah * 1.4, 0.3, 2.6)
    xg_a = np.clip(aa * 1.2, 0.3, 2.4)

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
        "Away Win %": round(away_win, 1)
    })

df_proj = pd.DataFrame(saida)

# =========================================================
# UI
# =========================================================
st.subheader("📊 Jogos Projetados (12 dias)")

if not df_proj.empty:
    st.dataframe(df_proj)
else:
    st.info("Sem jogos futuros no período.")
