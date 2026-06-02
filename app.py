import requests
import pandas as pd

# -----------------------------
# ESPN LOADER
# -----------------------------
def carregar_dados_online():

    ligas = {
        "Brasileirão - Série A": "bra.1",
        "Brasileirão - Série B": "bra.2",
        "Alemanha - Bundesliga": "ger.1",
        "Inglaterra - Premier League": "eng.1",
        "UEFA Champions League": "uefa.champions"
    }

    jogos = []

    for nome_liga, slug in ligas.items():

        url = f"https://site.web.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"

        try:
            r = requests.get(url, timeout=10)
            data = r.json()

            eventos = data.get("events", [])

            for e in eventos:

                comp = e.get("competitions", [{}])[0]
                status = comp.get("status", {}).get("type", {}).get("state")

                home = comp["competitors"][0]["team"]["displayName"]
                away = comp["competitors"][1]["team"]["displayName"]

                home_score = comp["competitors"][0].get("score")
                away_score = comp["competitors"][1].get("score")

                date = e.get("date")

                jogos.append({
                    "Date": pd.to_datetime(date),
                    "League": nome_liga,
                    "Home": home,
                    "Away": away,
                    "GOLS_HOME": float(home_score) if home_score is not None else None,
                    "GOLS_AWAY": float(away_score) if away_score is not None else None
                })

        except Exception as e:
            print(f"Erro ESPN {nome_liga}: {e}")

    return pd.DataFrame(jogos)
