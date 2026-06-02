import sys
import requests
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# =========================
# CONFIG
# =========================
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

st.set_page_config(page_title="LiveScanner Pro", layout="wide")

st.title("📊 LiveScanner Pro - ESPN MODE")

# =========================
# LIGAS PERMITIDAS (FILTRO OBRIGATÓRIO)
# =========================
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

# =========================
# ESPN LOADER (SÓ LIGAS DO MAPA)
# =========================
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

# =========================
# PESO TEMPORAL
# =========================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

# =========================
# FORÇA DO TIME (VERSÃO FINAL)
# =========================
def forca_time(team, side, data_ref, liga, l_home, l_away, df_hist):

    jogos_liga = df_hist[df_hist["League"] == liga]

    t = jogos_liga[jogos_liga["Home"] == team] if side == "home" else jogos_liga[jogos_liga["Away"] == team]

    if len(t) < 3:
        t = jogos_liga

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

# =========================
# DIXON COLES
# =========================
def dixon_coles(lh, la, rho=-0.1):
    p_h = poisson.pmf(np.arange(11), lh)
    p_a = poisson.pmf(np.arange(11), la)
    m = np.outer(p_h, p_a)

    m[0,0] *= (1 - lh * la * rho)
    m[0,1] *= (1 + lh * rho)
    m[1,0] *= (1 + la * rho)
    m[1,1] *= (1 - rho)

    return m / m.sum()

# =========================
# VALUE MODEL
# =========================
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

# =========================
# DADOS ESPN
# =========================
df = carregar_dados_online()

df_hist = df[df["GOLS_HOME"].notna()]
df_future = df[df["GOLS_HOME"].isna()]

saida = []

# =========================
# PROCESSAMENTO
# =========================
for _, r in df_future.iterrows():

    liga = r["League"]

    base_home = LIGAS_MAPA[liga]["base_home"]
    base_away = LIGAS_MAPA[liga]["base_away"]

    l_h = df_hist[df_hist["League"] == liga]["GOLS_HOME"].mean()
    l_a = df_hist[df_hist["League"] == liga]["GOLS_AWAY"].mean()

    if pd.isna(l_h):
        l_h, l_a = base_home, base_away

    ah, dh = forca_time(r["Home"], "home", r["Date"], liga, l_h, l_a, df_hist)
    aa, da = forca_time(r["Away"], "away", r["Date"], liga, l_h, l_a, df_hist)

    # =========================
    # xG (COM SUAVIZAÇÃO)
    # =========================
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

    placar = np.unravel_index(np.argmax(p), p.shape)
    placar_correto = f"{placar[0]}x{placar[1]}"

    val = detectar_melhor_valor(hw, d, aw, o15, o25, btts, xg_h + xg_a, r["Home"], r["Away"])

    saida.append({
        "Home": r["Home"],
        "Away": r["Away"],
        "League": liga,
        "Value": val,
        "xG": round(xg_h + xg_a, 2),
        "BTTS %": round(btts, 1),
        "Placar Provável": placar_correto
    })

# =========================
# UI
# =========================
if saida:
    for j in saida:
        st.markdown(f"""
        <div style="padding:15px;border:1px solid #ddd;border-radius:10px;margin-bottom:10px">
            <b>{j['Home']} vs {j['Away']}</b><br>
            <b>{j['League']}</b><br><br>
            <span style="background:#4F46E5;color:#fff;padding:5px 10px;border-radius:6px">
                {j['Value']}
            </span>
            <br><br>
            📊 xG: {j['xG']} | 🎯 BTTS: {j['BTTS %']}% | ⚽ {j['Placar Provável']}
        </div>
        """, unsafe_allow_html=True)
else:
    st.warning("Nenhum jogo encontrado na ESPN.")
