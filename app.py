import sys
import time
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import poisson

# Configuração de ambiente para Windows
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(page_title="LiveScanner Pro", page_icon="⚡", layout="wide")

# =========================================================
# DICIONÁRIO DE LIGAS (Mantido conforme sua estrutura)
# =========================================================
LIGAS_MAPA = {
    "Superettan": {"slug": "swe.2", "base_home": 1.55, "base_away": 1.20},
    "Brasileirão - Série A": {"slug": "bra.1", "base_home": 1.45, "base_away": 1.05},
    "Brasileirão - Série B": {"slug": "bra.2", "base_home": 1.35, "base_away": 0.95},
    "Alemanha - Bundesliga": {"slug": "ger.1", "base_home": 1.75, "base_away": 1.38}
}

# =========================================================
# MOTOR DE CAPTURA COM AJUSTE DE FUSO E DELAY
# =========================================================
@st.cache_data(ttl=600)
def carregar_dados_online():
    todos_jogos = []
    
    for nome_liga, config in LIGAS_MAPA.items():
        # URL com limit=1000 para capturar todo o calendário da temporada
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?dates=20260101-20261231&limit=1000"
        time.sleep(0.5) # Delay de proteção
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200: continue
            data = response.json()
            
            for event in data.get('events', []):
                status_type = event['status']['type']['name']
                # Converção de Fuso: API (UTC) -> Brasil (UTC-3)
                date_utc = pd.to_datetime(event['date'])
                date_brasil = date_utc.tz_convert('America/Sao_Paulo').tz_localize(None)
                
                comp = event['competitions'][0]
                competitors = comp['competitors']
                
                # Identificação segura do mandante e visitante
                home_team = next((c for c in competitors if c['homeAway'] == 'home'), None)
                away_team = next((c for c in competitors if c['homeAway'] == 'away'), None)
                
                if not home_team or not away_team: continue
                
                is_final = status_type in ["STATUS_FULL_TIME", "STATUS_FINAL"]
                h_score = int(home_team.get('score', 0)) if is_final else np.nan
                a_score = int(away_team.get('score', 0)) if is_final else np.nan
                
                uid = f"{nome_liga}_{date_brasil.strftime('%Y%m%d')}_{home_team['team']['displayName']}_{away_team['team']['displayName']}"
                
                todos_jogos.append({
                    "UID": uid, "League": nome_liga, "Date": date_brasil, "DateStr": date_brasil.strftime("%d/%m/%Y"),
                    "Time": date_brasil.strftime("%H:%M"), "Home": home_team['team']['displayName'], 
                    "Away": away_team['team']['displayName'], "GOLS_HOME": h_score, "GOLS_AWAY": a_score
                })
        except Exception as e:
            continue
            
    df = pd.DataFrame(todos_jogos)
    return df.drop_duplicates(subset=["UID"]) if not df.empty else df

# Execução Principal
df = carregar_dados_online()

if df.empty:
    st.error("Nenhum dado retornado da API. Verifique a conexão.")
    st.stop()

# --- Restante do seu código de processamento (Dixon-Coles, Exibição, etc) ---
st.success(f"Dados carregados com sucesso! Total de eventos: {len(df)}")
# O código de UI segue exatamente como você tinha, processando o DataFrame 'df'
                    })
            except Exception:
                continue

    # 2. CAPTURA DA BASE HISTÓRICA DE RETROSPECTO (MÉDIAS DE GOLS E Dixon-Coles)
    # Pega uma janela fixa retroativa para preencher o df_hist e alimentar a matemática
    url_hist = "20260101-20260601"
    for nome_liga, config in LIGAS_MAPA.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config['slug']}/scoreboard?dates={url_hist}&limit=300"
        try:
            response = requests.get(url, timeout=6)
            if response.status_code != 200: continue
            data = response.json()
            for event in data.get('events', []):
                status_type = event['status']['type']['name']
                if status_type not in ["STATUS_FULL_TIME", "STATUS_FINAL"]: continue
                
                date_utc = pd.to_datetime(event['date']).tz_convert('UTC')
                date_local = date_utc.tz_convert('America/Sao_Paulo')
                date_raw = date_local.replace(tzinfo=None)
                
                comp = event['competitions'][0]
                home_node = comp['competitors'][0]
                away_node = comp['competitors'][1]
                
                h_team = str(home_node['team']['displayName']).strip() if home_node['homeAway'] == 'home' else str(away_node['team']['displayName']).strip()
                a_team = str(away_node['team']['displayName']).strip() if away_node['homeAway'] == 'away' else str(home_node['team']['displayName']).strip()
                
                h_score = int(home_node['score']) if home_node['homeAway'] == 'home' else int(away_node['score'])
                a_score = int(away_node['score']) if away_node['homeAway'] == 'away' else int(home_node['score'])
                
                uid = f"HIST_{nome_liga}_{date_raw.strftime('%d%m%Y')}_{h_team}_vs_{a_team}".replace(" ", "_")
                todos_jogos.append({
                    "UID": uid, "League": nome_liga, "Date": date_raw, "DateStr": date_raw.strftime("%d/%m/%Y"),
                    "Time": date_raw.strftime("%H:%M"), "Home": h_team, "Away": a_team,
                    "GOLS_HOME": h_score, "GOLS_AWAY": a_score, "Score": f"{h_score}–{a_score}", "Status": status_type
                })
        except Exception:
            continue

    df = pd.DataFrame(todos_jogos)
    if not df.empty:
        df["TOTALGOALS"] = df["GOLS_HOME"] + df["GOLS_AWAY"]
        df = df.drop_duplicates(subset=["UID"], keep='first')
    return df

df = carregar_dados_online()

if df.empty:
    st.error("Nenhum dado pôde ser coletado das APIs online neste momento.")
    st.stop()

# =========================================================
# SEPARAÇÃO DINÂMICA INTEGRAL 
# =========================================================
df_future = df[df["GOLS_HOME"].isna()].copy()
df_hist = df[df["GOLS_HOME"].notna()].copy()

# =========================================================
# FUNÇÕES MATEMÁTICAS E PREDITIVAS (DIXON-COLES)
# =========================================================
def peso_temporal(data_jogo, data_ref, xi=0.0065):
    dias = (data_ref - data_jogo).dt.days
    return np.exp(-xi * dias)

def forca_time(team, side, data_ref, liga_jogo, l_home_mean, l_away_mean):
    if df_hist.empty: return 1.0, 1.0
    jogos = df_hist[(df_hist["Date"] < data_ref) & (df_hist["League"] == liga_jogo)].copy()
    t = jogos[jogos["Home"] == team] if side == "home" else jogos[jogos["Away"] == team]
    
    if len(t) == 0: return 1.0, 1.0
    t.loc[:, "peso"] = peso_temporal(t["Date"], data_ref)

    if side == "home":
        ataque = min(max(np.average(t["GOLS_HOME"], weights=t["peso"]) / l_home_mean, 0.5), 2.5)
        defesa = min(max(np.average(t["GOLS_AWAY"], weights=t["peso"]) / l_away_mean, 0.5), 2.5)
    else:
        ataque = min(max(np.average(t["GOLS_AWAY"], weights=t["peso"]) / l_away_mean, 0.5), 2.5)
        defesa = min(max(np.average(t["GOLS_HOME"], weights=t["peso"]) / l_home_mean, 0.5), 2.5)
    return ataque, defesa

def dixon_coles(lh, la, rho=-0.1, max_g=10):
    p_h = poisson.pmf(np.arange(max_g + 1), lh)
    p_a = poisson.pmf(np.arange(max_g + 1), la)
    m = np.outer(p_h, p_a)
    m[0, 0] *= (1 - lh * la * rho)
    m[0, 1] *= (1 + lh * rho)
    m[1, 0] *= (1 + la * rho)
    m[1, 1] *= (1 - rho)
    return m / m.sum()

def detectar_melhor_valor(hw, d, aw, o15, o25, u35, xg, home, away):
    if hw > 62.0: return f"🔥 A favor do Mandante: Vitória do {home}"
    if aw > 45.0: return f"🚀 A favor do Visitante: Vitória do {away}"
    if o25 > 57.0 and xg > 2.8: return "⚽ Jogo de Gols: Mais de 2.5 Gols"
    if d > 31.0 and u35 > 78.0 and xg < 2.25: return "🔒 Contra o Empate / Jogo Truncado"
    if o15 > 82.0 and o25 <= 57.0: return "🛡️ Segurança: Mais de 1.5 Gols"
    return "⚖️ Sem viés claro (Fique de Fora)"

def obter_melhor_opcao_anytime(p, home, away):
    opcoes = {
        f"1-0 favor {home} a Qualquer Momento": p[1:, 0:].sum() * 100,  
        f"0-1 favor {away} a Qualquer Momento": p[0:, 1:].sum() * 100,  
        f"1-1 a Qualquer Momento": p[1:, 1:].sum() * 100               
    }
    melhor_label = max(opcoes, key=opcoes.get)
    return melhor_label, opcoes[melhor_label]

# =========================================================
# EXIBIÇÃO DO SCANNER E SELETOR DE DATAS
# =========================================================
st.subheader("📊 Scanner de Mercado & Sinais Ativos")

saida = []
if not df_future.empty:
    for _, r in df_future.iterrows():
        data_ref = r["Date"]
        home = r["Home"]
        away = r["Away"]
        liga_corrente = r["League"]

        df_hist_liga = df_hist[df_hist["League"] == liga_corrente]
        liga_home_mean = max(df_hist_liga["GOLS_HOME"].mean(), 1.2) if not df_hist_liga.empty else LIGAS_MAPA[liga_corrente]["base_home"]
        liga_away_mean = max(df_hist_liga["GOLS_AWAY"].mean(), 1.0) if not df_hist_liga.empty else LIGAS_MAPA[liga_corrente]["base_away"]

        ah, dh = forca_time(home, "home", data_ref, liga_corrente, liga_home_mean, liga_away_mean)
        aa, da = forca_time(away, "away", data_ref, liga_corrente, liga_home_mean, liga_away_mean)

        xg_h = np.clip((ah * da * liga_home_mean), 0.3, 2.6)
        xg_a = np.clip((aa * dh * liga_away_mean), 0.3, 2.4)

        p = dixon_coles(xg_h, xg_a)
        home_win = np.sum(np.tril(p, -1)) * 100
        draw = np.sum(np.diag(p)) * 100
        away_win = np.sum(np.triu(p, 1)) * 100

        max_g = p.shape[0]
        gols_combinados = np.array([np.sum([p[i, j] for i in range(max_g) for j in range(max_g) if i + j == k]) for k in range(21)])

        over15 = (1 - gols_combinados[0] - gols_combinados[1]) * 100
        over25 = (1 - np.sum(gols_combinados[:3])) * 100
        under35 = np.sum(gols_combinados[:4]) * 100
        xg_total = xg_h + xg_a

        sugestao_value = detectar_melhor_valor(home_win, draw, away_win, over15, over25, under35, xg_total, home, away)
        lbl_anytime, prob_anytime = obter_melhor_opcao_anytime(p, home, away)

        saida.append({
            "Date": r["DateStr"], "Time": r["Time"], "Home": home, "Away": away, "League": liga_corrente,
            "💡 Sugestão Value": sugestao_value, "anytime_label": lbl_anytime, "anytime_prob": prob_anytime,
            "anytime_odd_justa": 100 / max(prob_anytime, 1.0), "Over 1.5 %": round(over15, 1), 
            "Over 2.5 %": round(over25, 1), "Under 3.5 %": round(under35, 1),
            "Home Win %": round(home_win, 1), "Draw %": round(draw, 1), "Away Win %": round(away_win, 1), "Expected Goals": round(xg_total, 2)
        })

if saida:
    df_proj = pd.DataFrame(saida)
    datas_disponiveis = sorted(df_proj["Date"].unique(), key=lambda x: pd.to_datetime(x, format="%d/%m/%Y"))
    
    col_sel, _ = st.columns([1, 3])
    with col_sel:
        data_selecionada = st.selectbox("🎯 Filtrar Rodada por Data (Próximos Jogos):", datas_disponiveis)
    
    df_proj_filtrado = df_proj[df_proj["Date"] == data_selecionada]

    for _, jogo in df_proj_filtrado.iterrows():
        st.markdown(f"""
        <div class="match-box" style="margin-bottom: 0px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;">
            <div class="match-header">
                <span>📅 Evento: {jogo['Date']} - {jogo['Time']} | Projeção Quantitativa Dixon-Coles</span>
                <span class="league-badge">{jogo['League']}</span>
            </div>
            <div class="row" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 280px;">
                    <span class="team-name">{jogo['Home']}</span>
                    <span class="vs-badge">VS</span>
                    <span class="team-name">{jogo['Away']}</span>
                    <div style="margin-top: 12px;">
                        <span class="value-badge">{jogo['💡 Sugestão Value']}</span>
                        <span style="margin-left: 10px; font-size:13px; color:#475569; font-weight:bold;">📊 xG Estimado: {jogo['Expected Goals']}</span>
                    </div>
                </div>
                <div style="flex: 1.5; min-width: 350px; display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin-top: 10px;">
                    <div><div class="market-title">Casa</div><div class="odd-box-back">{jogo['Home Win %']}%</div></div>
                    <div><div class="market-title">Empate</div><div class="odd-box-lay">{jogo['Draw %']}%</div></div>
                    <div><div class="market-title">Fora</div><div class="odd-box-back">{jogo['Away Win %']}%</div></div>
                    <div><div class="market-title">Mais 1.5</div><div class="odd-box-goals">{jogo['Over 1.5 %']}%</div></div>
                    <div><div class="market-title">Mais 2.5</div><div class="odd-box-goals">{jogo['Over 2.5 %']}%</div></div>
                    <div><div class="market-title">Menos 3.5</div><div class="odd-box-goals">{jogo['Under 3.5 %']}%</div></div>
                </div>
            </div>
        </div>
        
        <div class="value-report-box" style="margin-top: -1px; margin-bottom: 1.5rem; border-top-left-radius: 0px; border-top-right-radius: 0px; border-top: none;">
            <div class="report-topic">🎯 Oportunidade Elite: Resultado a Qualquer Momento <span class="badge-value">HÁ VALOR DETECTADO</span></div>
            <div class="report-text" style="margin-top: 6px;">
                <b>Entrada Selecionada:</b> {jogo['anytime_label']}<br>
                <b>Probabilidade de Ocorrência:</b> {jogo['anytime_prob']:.1f}% | <b>Odd Justa Limite:</b> {jogo['anytime_odd_justa']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📊 Histograma de Linhas de Gols Ativas (Soma de xG)")
    
    fig, ax = plt.subplots(figsize=(12, 4), facecolor='#1E293B')
    ax.set_facecolor('#0F172A')
    
    confrontos = df_proj_filtrado["Home"] + " vs " + df_proj_filtrado["Away"]
    bars = ax.bar(confrontos, df_proj_filtrado["Expected Goals"], color='#06B6D4', edgecolor='#0891B2', alpha=0.85, width=0.3)
    
    media_liga = df_proj_filtrado["Expected Goals"].mean() if not df_proj_filtrado.empty else 2.5
    ax.axhline(media_liga, color='#F43F5E', linestyle='--', linewidth=1.5, label=f'Média de xG do Dia: {media_liga:.2f}')
    
    ax.set_ylabel("Expected Goals Total", fontsize=10, color='#94A3B8')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='both', colors='#94A3B8', labelsize=9)
    ax.grid(axis='y', linestyle=':', alpha=0.2, color='#94A3B8')
    
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points", ha='center', va='bottom', fontsize=9, color='#06B6D4', fontweight='bold')

    plt.xticks(rotation=10, ha='right')
    plt.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='white')
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info("Nenhum confronto futuro sem resultado foi retornado para a janela de 14 dias.")
