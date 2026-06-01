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
    page_title="QuantumScanner Pro - Pesos por Liga v3.9",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #060913; color: #F0F4F8; }
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    footer {visibility: hidden;}
    [data-testid="stHeader"] { background: rgba(6, 19, 19, 0.8); backdrop-filter: blur(8px); }
    
    .metric-card { background-color: #0F172A; padding: 1.2rem; border-radius: 12px; border-left: 4px solid #10B981; color: white; border: 1px solid #1E293B; }
    .metric-title { font-size: 11px; text-transform: uppercase; color: #94A3B8; letter-spacing: 1px; font-weight: bold; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #10B981; margin-top: 2px; }
    
    .match-box { background: #0F172A; border: 1px solid #1E293B; border-radius: 12px; padding: 1.5rem; }
    .match-header { font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase; margin-bottom: 0.8rem; border-bottom: 1px solid #1E293B; padding-bottom: 6px; display: flex; justify-content: space-between; }
    .league-badge { background: #1E293B; color: #38BDF8; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; }
    .team-name { font-size: 1.35rem; font-weight: 800; color: #F8FAFC; }
    .vs-badge { font-size: 10px; background: #1E293B; color: #94A3B8; padding: 2px 8px; border-radius: 4px; margin: 0 10px; font-weight: bold; }
    
    .market-title { font-size: 10px; font-weight: bold; color: #64748B; text-transform: uppercase; text-align: center; margin-bottom: 4px; letter-spacing: 0.5px; }
    .odd-box-back { background: #075985; border: 1px solid #0369A1; color: #38BDF8; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .odd-box-lay { background: #1E1B4B; border: 1px solid #312E81; color: #818CF8; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .odd-box-goals { background: #064E3B; border: 1px solid #065F46; color: #34D399; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    
    .value-badge { background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%); color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; display: inline-block; border: 1px solid #6366F1; }
    .value-report-box { background: #090D1A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px; }
    .report-topic { font-size: 11px; font-weight: 700; color: #818CF8; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
    .report-text { font-size: 13px; color: #94A3B8; line-height: 1.5; margin-bottom: 4px; }
    .badge-value { background: #064E3B; color: #34D399; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; border: 1px solid #059669; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p style="color:#6366F1; font-weight:bold; text-transform:uppercase; font-size:12px; margin-bottom:0; letter-spacing: 2px;">⚡ QUANTUM RADAR SELETIVO v3.9</p>', unsafe_allow_html=True)
st.markdown('<h1 style="color:white; font-size:2.6rem; font-weight:900; margin-top:0;">📊 TERMINAL QUANTUM: Validação Estatística Fina</h1>', unsafe_allow_html=True)
st.markdown("---")

# =========================================================
# LIGAS OPERACIONAIS CORRIGIDAS - SEM MISTURA DE ENDPOINTS
# =========================================================
LIGAS_DE_VALOR = {
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.42, "base_away": 1.02},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.20, "base_away": 0.85},
    "Brasileirão - Feminino": {"slug": "bra.women.1", "base_home": 1.58, "base_away": 1.18},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38},
    "Copa do Mundo 2026": {"slug": "fifa.world", "base_home": 1.52, "base_away": 1.18},
    "Suécia - Allsvenskan": {"slug": "swe.1", "base_home": 1.65, "base_away": 1.28},
    "Suécia - Superettan": {"slug": "swe.2", "base_home": 1.52, "base_away": 1.20},
    "Noruega - Eliteserien": {"slug": "nor.1", "base_home": 1.70, "base_away": 1.35},
    "UEFA Champions League": {"slug": "uefa.champions", "base_home": 1.60, "base_away": 1.25},
    "Copa Libertadores": {"slug": "conmebol.libertadores", "base_home": 1.45, "base_away": 1.05},
    "Copa Sudamericana": {"slug": "conmebol.sudamericana", "base_home": 1.35, "base_away": 0.95},
    "Chile - Primera División": {"slug": "chi.1", "base_home": 1.44, "base_away": 1.12},
    "Equador - LigaPro": {"slug": "ecu.1", "base_home": 1.48, "base_away": 1.05},
    "EUA - MLS": {"slug": "usa.1", "base_home": 1.68, "base_away": 1.30},
    "Holanda - Eredivisie": {"slug": "ned.1", "base_home": 1.78, "base_away": 1.40},
    "Islândia - Urvalsdeild": {"slug": "isl.1", "base_home": 1.85, "base_away": 1.42}
}

# =========================================================
# MOTOR DE CAPTURA E SEGREGAÇÃO DE DADOS
# =========================================================
@st.cache_data(ttl=600)
def escaneamento_ligas_valor():
    todos_jogos = []
    
    for nome_liga, config in LIGAS_DE_VALOR.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200: continue
            data = response.json()
            
            for event in data.get('events', []):
                status_type = event['status']['type']['name']
                date_raw = pd.to_datetime(event['date'])
                
                comp = event['competitions'][0]
                home_node = comp['competitors'][0]
                away_node = comp['competitors'][1]
                
                h_team = home_node['team']['displayName'] if home_node['homeAway'] == 'home' else away_node['team']['displayName']
                a_team = away_node['team']['displayName'] if away_node['homeAway'] == 'away' else home_node['team']['displayName']
                
                h_score = np.nan
                a_score = np.nan
                
                if status_type in ["STATUS_FULL_TIME", "STATUS_FINAL"]:
                    h_score = int(home_node['score']) if home_node['homeAway'] == 'home' else int(away_node['score'])
                    a_score = int(away_node['score']) if away_node['homeAway'] == 'away' else int(home_node['score'])

                todos_jogos.append({
                    "Liga": nome_liga,
                    "DateObj": date_raw,
                    "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "TimeStr": date_raw.strftime("%H:%M"),
                    "Home": str(h_team).strip(),
                    "Away": str(a_team).strip(),
                    "GOLS_HOME": h_score,
                    "GOLS_AWAY": a_score
                })
        except Exception:
            continue
            
    df = pd.DataFrame(todos_jogos)
    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]
    return df

df_global = escaneamento_ligas_valor()

if df_global.empty:
    st.error("Nenhum dado ativo retornado para as ligas selecionadas.")
    st.stop()

df_hist = df_global[df_global["GOLS_HOME"].notna()].copy()
df_future = df_global[df_global["GOLS_HOME"].isna()].copy()

# =========================================================
# FUNÇÕES MATEMÁTICAS AJUSTADAS COM FILTRO LOCAL REAL
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    return np.exp(-xi * (data_ref - data_jogo).dt.days)

def forca_time(team, side, data_ref, liga_filtrada, l_home_mean, l_away_mean):
    df_contexto = df_hist[df_hist["Liga"] == liga_filtrada]
    if df_contexto.empty: 
        return 1.0, 1.0
    
    jogos = df_contexto[df_contexto["DateObj"] < data_ref].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    if len(t) == 0: 
        return 1.0, 1.0

    t.loc[:, "peso"] = peso_temporal(t["DateObj"], data_ref)
    if side == "home":
        atk = np.average(t["GOLS_HOME"], weights=t["peso"])
        def_ = np.average(t["GOLS_AWAY"], weights=t["peso"])
        return (atk / max(l_home_mean, 0.5)), (def_ / max(l_away_mean, 0.5))
    else:
        atk = np.average(t["GOLS_AWAY"], weights=t["peso"])
        def_ = np.average(t["GOLS_HOME"], weights=t["peso"])
        return (atk / max(l_away_mean, 0.5)), (def_ / max(l_home_mean, 0.5))

def dixon_coles(lh, la, rho=-0.07, max_g=9):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)
    m[0, 0] *= (1 - lh * la * rho); m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho); m[1, 1] *= (1 - rho)
    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg, btts, home, away):
    if o25 > 56.5 and xg > 2.80 and btts > 56.0: return "⚽ Ultra Valor: Mais de 2.5 & Ambas Marcam"
    if hw > 62.0: return f"🔥 Vitória do Mandante: {home}"
    if aw > 45.0: return f"🚀 Vitória do Visitante: {away}"
    if o15 > 82.0 and o25 <= 56.5: return "🛡️ Segurança: Mais de 1.5 Gols"
    if d > 32.0 and u35 > 76.5 and xg < 2.15: return "🔒 Contra o Empate / Truncado"
    return "⚖️ Sem viés claro (Fique de Fora)"

def obter_melhor_opcao_anytime(p, home, away):
    opcoes = {
        f"1-0 favor {home} a Qualquer Momento": p[1:, 0:].sum() * 100,  
        f"2-0 favor {home} a Qualquer Momento": p[2:, 0:].sum() * 100,  
        f"2-1 favor {home} a Qualquer Momento": p[2:, 1:].sum() * 100,  
        f"0-1 favor {away} a Qualquer Momento": p[0:, 1:].sum() * 100,  
        f"0-2 favor {away} a Qualquer Momento": p[0:, 2:].sum() * 100,  
        f"1-1 a Qualquer Momento": p[1:, 1:].sum() * 100               
    }
    melhor_label = max(opcoes, key=opcoes.get)
    return melhor_label, opcoes[melhor_label]

# =========================================================
# PROCESSAMENTO DOS CONFRONTOS FUTUROS
# =========================================================
if not df_future.empty:
    saida_global = []
    for _, r in df_future.iterrows():
        liga, data_ref, home, away, hora_jogo = r["Liga"], r["DateObj"], r["Home"], r["Away"], r["TimeStr"]
        
        # Ajuste dinâmico restrito da liga corrente
        df_contexto_liga = df_hist[df_hist["Liga"] == liga]
        if not df_contexto_liga.empty and len(df_contexto_liga) >= 4:
            liga_home_mean = df_contexto_liga["GOLS_HOME"].mean()
            liga_away_mean = df_contexto_liga["GOLS_AWAY"].mean()
        else:
            liga_home_mean = LIGAS_DE_VALOR.get(liga, {}).get("base_home", 1.50)
            liga_away_mean = LIGAS_DE_VALOR.get(liga, {}).get("base_away", 1.15)
            
        ah, dh = forca_time(home, "home", data_ref, liga, liga_home_mean, liga_away_mean)
        aa, da = forca_time(away, "away", data_ref, liga, liga_home_mean, liga_away_mean)

        # Cálculo do xG Real Modulado individualmente pelo peso real do campeonato
        xg_h = np.clip(((ah * da * liga_home_mean) * 0.70 + liga_home_mean * 0.30), 0.25, 3.6)
        xg_a = np.clip(((aa * dh * liga_away_mean) * 0.70 + liga_away_mean * 0.30), 0.25, 3.3)

        # Evita distorções de fallbacks estáticos duplicados idênticos mudando levemente por força base
        if ah == 1.0 and aa == 1.0:
            xg_h += 0.05
            xg_a -= 0.05

        p = dixon_coles(xg_h, xg_a)
        home_win = np.sum(np.tril(p, -1)) * 100
        draw = np.sum(np.diag(p)) * 100
        away_win = np.sum(np.triu(p, 1)) * 100

        max_g = p.shape[0]
        gols_comb = np.array([np.sum([p[i, j] for i in range(max_g) for j in range(max_g) if i + j == k]) for k in range(15)])

        over15 = (1 - gols_comb[0] - gols_comb[1]) * 100
        over25 = (1 - np.sum(gols_comb[:3])) * 100
        under35 = np.sum(gols_comb[:4]) * 100
        xg_total = xg_h + xg_a
        
        btts_prob = (1 - p[0, :].sum() - p[:, 0].sum() + p[0, 0]) * 100

        sugestao_value = detectar_melhor_valor(home_win, draw, away_win, over15, over25, under35, xg_total, btts_prob, home, away)
        lbl_anytime, prob_anytime = obter_melhor_opcao_anytime(p, home, away)

        saida_global.append({
            "Liga": liga, "Date": r["DateStr"], "Hora": hora_jogo, "Home": home, "Away": away, 
            "Sugestao": sugestao_value, "anytime_label": lbl_anytime, "anytime_prob": prob_anytime, 
            "anytime_odd_justa": 100 / max(prob_anytime, 1.0), "Over15": over15, "Over25": over25, 
            "Under35": under35, "HomeWin": home_win, "Draw": draw, "AwayWin": away_win, "xG": xg_total,
            "BTTS": btts_prob, "Timestamp": data_ref
        })

    df_processado = pd.DataFrame(saida_global)
    df_processado = df_processado.sort_values(by="Timestamp")
    datas_com_jogos = df_processado["Date"].unique().tolist()
    
    st.markdown("### 📅 Central de Análise de Sinais")
    col_sel, _ = st.columns([1, 2])
    with col_sel:
        data_selecionada = st.selectbox("🎯 Escolha o Dia Operacional:", datas_com_jogos)
        
    df_final_dia = df_processado[df_processado["Date"] == data_selecionada]
    
    st.markdown(f"""
        <div class="kpi-wrapper" style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
            <div class="metric-card"><div class="metric-title">Jogos de Valor Encontrados</div><div class="metric-value">{len(df_final_dia)}</div></div>
            <div class="metric-card" style="border-left-color: #38BDF8;"><div class="metric-title">Ligas Ativas no Dia</div><div class="metric-value">{df_final_dia['Liga'].nunique()}</div></div>
        </div>
    """, unsafe_allow_html=True)

    for _, jogo in df_final_dia.iterrows():
        st.markdown(f"""
        <div class="match-box" style="margin-bottom: 0px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; margin-top:10px;">
            <div class="match-header">
                <span>📅 {jogo['Date']} - {jogo['Hora']}</span> 
                <span class="league-badge">{jogo['Liga']}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap:15px;">
                <div style="flex: 1; min-width: 280px;">
                    <span class="team-name">{jogo['Home']}</span>
                    <span class="vs-badge">VS</span>
                    <span class="team-name">{jogo['Away']}</span>
                    <div style="margin-top: 12px;">
                        <span class="value-badge">{jogo['Sugestao']}</span>
                        <span style="margin-left: 10px; font-size:13px; color:#94A3B8; font-weight:bold;">📊 xG Calculado: {jogo['xG']:.2f} | BTTS: {jogo['BTTS']:.1f}%</span>
                    </div>
                </div>
                <div style="flex: 1.5; min-width: 350px; display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px;">
                    <div><div class="market-title">Casa</div><div class="odd-box-back">{jogo['HomeWin']:.1f}%</div></div>
                    <div><div class="market-title">Empate</div><div class="odd-box-lay">{jogo['Draw']:.1f}%</div></div>
                    <div><div class="market-title">Fora</div><div class="odd-box-back">{jogo['AwayWin']:.1f}%</div></div>
                    <div><div class="market-title">Over 1.5</div><div class="odd-box-goals">{jogo['Over15']:.1f}%</div></div>
                    <div><div class="market-title">Over 2.5</div><div class="odd-box-goals">{jogo['Over25']:.1f}%</div></div>
                    <div><div class="market-title">Under 3.5</div><div class="odd-box-goals">{jogo['Under35']:.1f}%</div></div>
                </div>
            </div>
        </div>
        <div class="value-report-box" style="margin-top: -1px; margin-bottom: 1.5rem; border-top-left-radius: 0px; border-top-right-radius: 0px; border-top: none;">
            <div class="report-topic">🎯 Oportunidade Elite: Submercados <span class="badge-value">VALOR OPERACIONAL MATEMÁTICO</span></div>
            <div class="report-text" style="margin-top: 4px;">
                <b>Cenário Probabilístico (Anytime):</b> {jogo['anytime_label']}<br>
                <b>Métrica Estatística:</b> {jogo['anytime_prob']:.1f}% | <b>Odd Justa Mínima Calculada:</b> {jogo['anytime_odd_justa']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Nenhum confronto futuro mapeado para o conjunto restrito de ligas de valor nas próximas 72 horas.")
