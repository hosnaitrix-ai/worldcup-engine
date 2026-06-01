import sys
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

# Evita problemas de concorrência com loops assíncronos no Windows
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# =========================================================
# CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL TRADING
# =========================================================
st.set_page_config(
    page_title="QuantumScanner Pro - Terminal Multiligas",
    page_icon="⚡",
    layout="wide"
)

# CSS Customizado: Interface Dark-Mode Premium de Alta Performance
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #060913; color: #F0F4F8; }
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    footer {visibility: hidden;}
    [data-testid="stHeader"] { background: rgba(6, 19, 19, 0.8); backdrop-filter: blur(8px); }
    
    /* Grid de Métricas da Liga */
    .metric-card { background-color: #0F172A; padding: 1.2rem; border-radius: 12px; border-left: 4px solid #10B981; color: white; border: 1px solid #1E293B; }
    .metric-title { font-size: 11px; text-transform: uppercase; color: #94A3B8; letter-spacing: 1px; font-weight: bold; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #10B981; margin-top: 2px; }
    
    /* Layout dos Cards de Jogos (Trading Pro) */
    .match-box { background: #0F172A; border: 1px solid #1E293B; border-radius: 12px; padding: 1.5rem; }
    .match-header { font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase; margin-bottom: 0.8rem; border-bottom: 1px solid #1E293B; padding-bottom: 6px; display: flex; justify-content: space-between; }
    .team-name { font-size: 1.35rem; font-weight: 800; color: #F8FAFC; }
    .vs-badge { font-size: 10px; background: #1E293B; color: #94A3B8; padding: 2px 8px; border-radius: 4px; margin: 0 10px; font-weight: bold; }
    
    /* Odds e Mercados */
    .market-title { font-size: 10px; font-weight: bold; color: #64748B; text-transform: uppercase; text-align: center; margin-bottom: 4px; letter-spacing: 0.5px; }
    .odd-box-back { background: #075985; border: 1px solid #0369A1; color: #38BDF8; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .odd-box-lay { background: #1E1B4B; border: 1px solid #312E81; color: #818CF8; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    .odd-box-goals { background: #064E3B; border: 1px solid #065F46; color: #34D399; text-align: center; padding: 8px; border-radius: 6px; font-weight: 800; font-size: 15px; }
    
    /* Badge de Sugestão de Entrada */
    .value-badge { background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%); color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; display: inline-block; border: 1px solid #6366F1; }

    /* DESIGN DO BLOCO DE RELATÓRIO ANYTIME INTEGRADO */
    .value-report-box { background: #090D1A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px; }
    .report-topic { font-size: 11px; font-weight: 700; color: #818CF8; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
    .report-text { font-size: 13px; color: #94A3B8; line-height: 1.5; margin-bottom: 4px; }
    .badge-value { background: #064E3B; color: #34D399; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; border: 1px solid #059669; }
    </style>
""", unsafe_allow_html=True)

# Top Bar do Terminal
st.markdown('<p style="color:#6366F1; font-weight:bold; text-transform:uppercase; font-size:12px; margin-bottom:0; letter-spacing: 2px;">⚡ QUANTUM CORE ENGILINE v2.0</p>', unsafe_allow_html=True)
st.markdown('<h1 style="color:white; font-size:2.6rem; font-weight:900; margin-top:0;">📊 TRADING PRO: Terminal Multiligas</h1>', unsafe_allow_html=True)
st.markdown("---")

# =========================================================
# CENTRAL DE MAPEAMENTO DE LIGAS ELITE (ESPN API ENDPOINTS)
# =========================================================
LIGAS_DISPONIVEIS = {
    "Suécia - Allsvenskan": "fifa.allsvenskan",
    "Noruega - Eliteserien": "fifa.eliteserien",
    "Inglaterra - Premier League": "eng.1",
    "UEFA Champions League": "uefa.champions",
    "Espanha - LaLiga": "esp.1",
    "Itália - Serie A": "ita.1",
    "Alemanha - Bundesliga": "ger.1",
    "França - Ligue 1": "fra.1",
    "Holanda - Eredivisie": "ned.1",
    "Portugal - Liga Portugal": "por.1",
    "Brasil - Série A": "bra.1",
    "Copa do Mundo (Eliminatórias)": "fifa.worldq",
    "EUA - MLS": "usa.1",
    "Argentina - Primera División": "arg.1"
}

# Interface de Seleção no Menu Lateral (Excelente para Mobile)
st.sidebar.markdown("### 🌐 CONFIGURAÇÃO DE FLUXO")
liga_selecionada = st.sidebar.selectbox("Escolha a Liga Alvo:", list(LIGAS_DISPONIVEIS.keys()))
endpoint_liga = LIGAS_DISPONIVEIS[liga_selecionada]

# =========================================================
# INGESTÃO DE DADOS AO VIVO VIA API
# =========================================================
@st.cache_data(ttl=900)  # Limpa o cache a cada 15 minutos de forma inteligente
def carregar_dados_live(slug_liga):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug_liga}/scoreboard"
    try:
        response = requests.get(url, timeout=12)
        data = response.json()
        jogos_lista = []
        
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

            jogos_lista.append({
                "DateObj": date_raw,
                "DateStr": date_raw.strftime("%d/%m/%Y"),
                "TimeStr": date_raw.strftime("%H:%M"),
                "Home": str(h_team).strip(),
                "Away": str(a_team).strip(),
                "GOLS_HOME": h_score,
                "GOLS_AWAY": a_score
            })
            
        df = pd.DataFrame(jogos_lista)
        if not df.empty:
            df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]
        return df
    except Exception:
        return pd.DataFrame(columns=["DateObj", "DateStr", "TimeStr", "Home", "Away", "GOLS_HOME", "GOLS_AWAY", "TOTALGOALS"])

df = carregar_dados_live(endpoint_liga)

if df.empty:
    st.error(f"Sem conexões ativas ou jogos disponíveis para {liga_selecionada} na API neste momento.")
    st.stop()

# Divisão estratégica de histórico vs prospecção futura
df_hist = df[df["GOLS_HOME"].notna()].copy()
df_future = df[df["GOLS_HOME"].isna()].copy()

# Tratamento Fairline adaptável
liga_home = max(df_hist["GOLS_HOME"].mean(), 1.45) if not df_hist.empty else 1.55
liga_away = max(df_hist["GOLS_AWAY"].mean(), 1.15) if not df_hist.empty else 1.20

# =========================================================
# ENGINE MATEMÁTICA QUANTITATIVA
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref):
    if df_hist.empty: return 1.0, 1.0
    jogos = df_hist[df_hist["DateObj"] < data_ref].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    
    if len(t) == 0: return 1.0, 1.0

    t.loc[:, "peso"] = peso_temporal(t["DateObj"], data_ref)

    if side == "home":
        atk = np.average(t["GOLS_HOME"], weights=t["peso"])
        def_ = np.average(t["GOLS_AWAY"], weights=t["peso"])
        return (atk / liga_home), (def_ / liga_away)
    else:
        atk = np.average(t["GOLS_AWAY"], weights=t["peso"])
        def_ = np.average(t["GOLS_HOME"], weights=t["peso"])
        return (atk / liga_away), (def_ / liga_home)

def dixon_coles(lh, la, rho=-0.08, max_g=9):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)
    m[0, 0] *= (1 - lh * la * rho); m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho); m[1, 1] *= (1 - rho)
    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg, home, away):
    if hw > 60.0: return f"🔥 Vitória do Mandante: {home}"
    if aw > 44.0: return f"🚀 Vitória do Visitante: {away}"
    if o25 > 56.0 and xg > 2.75: return "⚽ Jogo de Gols: Mais de 2.5 Gols"
    if d > 32.0 and u35 > 76.0 and xg < 2.20: return "🔒 Contra o Empate / Jogo Truncado"
    if o15 > 80.0 and o25 <= 56.0: return "🛡️ Segurança: Mais de 1.5 Gols"
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
# CRUNCHING E PROCESSAMENTO DE MERCADO
# =========================================================
st.subheader("📊 Scanner de Sinais Ativos")

saida = []
if not df_future.empty:
    for _, r in df_future.iterrows():
        data_ref, home, away, hora_jogo = r["DateObj"], r["Home"], r["Away"], r["TimeStr"]
        ah, dh = forca_time(home, "home", data_ref)
        aa, da = forca_time(away, "away", data_ref)

        xg_h = np.clip(((ah * da * liga_home) * 0.7 + liga_home * 0.3), 0.2, 3.5)
        xg_a = np.clip(((aa * da * liga_away) * 0.7 + liga_away * 0.3), 0.2, 3.2)

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

        sugestao_value = detectar_melhor_valor(home_win, draw, away_win, over15, over25, under35, xg_total, home, away)
        lbl_anytime, prob_anytime = obter_melhor_opcao_anytime(p, home, away)

        saida.append({
            "Date": r["DateStr"], "Hora": hora_jogo, "Home": home, "Away": away, 
            "Sugestao": sugestao_value, "anytime_label": lbl_anytime, "anytime_prob": prob_anytime, 
            "anytime_odd_justa": 100 / max(prob_anytime, 1.0), "Over15": over15, "Over25": over25, 
            "Under35": under35, "HomeWin": home_win, "Draw": draw, "AwayWin": away_win, "xG": xg_total
        })

    df_proj = pd.DataFrame(saida)
    datas_disponiveis = sorted(df_proj["Date"].unique())
    
    col_sel, _ = st.columns([1, 3])
    with col_sel:
        data_selecionada = st.selectbox("🎯 Filtrar Rodada por Data:", datas_disponiveis)
    
    df_proj_filtrado = df_proj[df_proj["Date"] == data_selecionada]

    # Renderização Estilo Trading Pro Premium Dark
    for _, jogo in df_proj_filtrado.iterrows():
        st.markdown(f"""
        <div class="match-box" style="margin-bottom: 0px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;">
            <div class="match-header"><span>📅 DATA: {jogo['Date']} - {jogo['Hora']}</span> <span>PROJEÇÃO QUANTITATIVA DIXON-COLES</span></div>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap:15px;">
                <div style="flex: 1; min-width: 280px;">
                    <span class="team-name">{jogo['Home']}</span>
                    <span class="vs-badge">VS</span>
                    <span class="team-name">{jogo['Away']}</span>
                    <div style="margin-top: 12px;">
                        <span class="value-badge">{jogo['Sugestao']}</span>
                        <span style="margin-left: 10px; font-size:13px; color:#94A3B8; font-weight:bold;">📊 xG: {jogo['xG']:.2f}</span>
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
            <div class="report-topic">🎯 Oportunidade Elite: Anytime Market <span class="badge-value">VALOR OPERACIONAL</span></div>
            <div class="report-text" style="margin-top: 4px;">
                <b>Cenário Alvo:</b> {jogo['anytime_label']}<br>
                <b>Probabilidade Estatística:</b> {jogo['anytime_prob']:.1f}% | <b>Odd Justa Limite (Fairline):</b> {jogo['anytime_odd_justa']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Monitor de Tendência Gráfico
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📊 Histograma de Linhas de Gols Ativas (Soma de xG)")
    
    fig, ax = plt.subplots(figsize=(12, 3.8), facecolor='#060913')
    ax.set_facecolor('#0F172A')
    confrontos = df_proj_filtrado["Home"] + " vs " + df_proj_filtrado["Away"]
    bars = ax.bar(confrontos, df_proj_filtrado["xG"], color='#38BDF8', edgecolor='#0284C7', alpha=0.85, width=0.3)
    
    ax.axhline(liga_home + liga_away, color='#F43F5E', linestyle='--', linewidth=1.5, label='Fairline Estimada')
    ax.set_ylabel("Expected Goals Total", fontsize=10, color='#94A3B8')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#1E293B'); ax.spines['bottom'].set_color('#1E293B')
    ax.tick_params(axis='both', colors='#94A3B8', labelsize=9)
    plt.xticks(rotation=10, ha='right')
    plt.legend(frameon=True, facecolor='#0F172A', edgecolor='#1E293B', labelcolor='white')
    plt.tight_layout()
    st.pyplot(fig)

else:
    st.info("Nenhum confronto futuro pendente de encerramento foi mapeado para esta liga nas próximas 48 horas.")

# =========================================================
# CENTRAL DE LIQUIDEZ HISTÓRICA DA LIGA
# =========================================================
st.markdown("---")
with st.expander("🗂️ Central de Liquidez e Estatísticas Gerais da Liga"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Amostragem Coletada</div><div class="metric-value">{len(df_hist)} Jogos</div></div>', unsafe_allow_html=True)
    with col2:
        media_g_hist = df_hist["TOTALGOALS"].mean() if not df_hist.empty else (liga_home + liga_away)
        st.markdown(f'<div class="metric-card"><div class="metric-title">Média de Gols (Histórico)</div><div class="metric-value">{media_g_hist:.2f}</div></div>', unsafe_allow_html=True)
    with col3:
        pct_over = (df_hist["TOTALGOALS"] > 2.5).mean() * 100 if not df_hist.empty else 52.5
        st.markdown(f'<div class="metric-card"><div class="metric-title">Liquidez de Over 2.5 FT</div><div class="metric-value">{pct_over:.1f}%</div></div>', unsafe_allow_html=True)
