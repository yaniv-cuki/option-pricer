"""
Genere un instantane des chaines d'options.

Yahoo Finance limite les requetes provenant des serveurs cloud (HTTP 429 sur
la recuperation du jeton d'authentification). L'application deployee ne peut
donc pas toujours acceder aux chaines d'options en direct, alors que les prix
spot passent sans probleme.

Ce script se lance EN LOCAL, ou l'acces fonctionne, et enregistre un
instantane que l'application utilise comme source de repli.

Usage :  python3 generer_snapshot.py
"""

import json
from datetime import datetime
from pathlib import Path

import yfinance as yf

# Sous-jacents pour lesquels on conserve un instantane.
TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",
           "TSLA", "AMD", "SPY", "QQQ"]

# Echeances retenues : on saute les toutes premieres (quelques jours, donnees
# instables) et on s'arrete avant les tres lointaines (peu liquides).
INDICES_ECHEANCES = range(5, 12)

# On ne garde que les strikes autour de la monnaie : au-dela, les contrats
# sont peu echanges et leurs prix sont perimes.
BANDE_STRIKES = 0.25

FICHIER_SORTIE = Path("snapshot_options.json")


def extraire_contrats(tableau, spot):
    """Ne conserve que strike et dernier prix, dans la bande utile."""
    contrats = []

    for _, ligne in tableau.iterrows():
        strike = float(ligne["strike"])
        prix = float(ligne["lastPrice"])

        if prix <= 0:
            continue
        if not (spot * (1 - BANDE_STRIKES) < strike < spot * (1 + BANDE_STRIKES)):
            continue

        contrats.append({"strike": strike, "lastPrice": prix})

    return contrats


def collecter(symbole):
    """Recupere spot et chaines d'options pour un sous-jacent."""
    tk = yf.Ticker(symbole)

    historique = tk.history(period="5d")
    if historique.empty:
        print(f"  {symbole} : pas de donnees de prix, ignore")
        return None

    spot = float(historique["Close"].iloc[-1])
    dates = list(tk.options)

    if not dates:
        print(f"  {symbole} : aucune echeance disponible, ignore")
        return None

    echeances = {}

    for idx in INDICES_ECHEANCES:
        if idx >= len(dates):
            continue

        date = dates[idx]

        try:
            chaine = tk.option_chain(date)
        except Exception as e:
            print(f"  {symbole} {date} : echec ({type(e).__name__}), ignore")
            continue

        calls = extraire_contrats(chaine.calls, spot)
        puts = extraire_contrats(chaine.puts, spot)

        if len(calls) + len(puts) < 10:
            print(f"  {symbole} {date} : trop peu de contrats, ignore")
            continue

        echeances[date] = {"calls": calls, "puts": puts}
        print(f"  {symbole} {date} : {len(calls)} calls, {len(puts)} puts")

    if not echeances:
        return None

    return {"spot": spot, "expiries": echeances}


def main():
    print("Generation de l'instantane des chaines d'options\n")

    donnees = {
        "genere_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tickers": {},
    }

    for symbole in TICKERS:
        print(f"{symbole} :")
        resultat = collecter(symbole)

        if resultat is not None:
            donnees["tickers"][symbole] = resultat

        print()

    if not donnees["tickers"]:
        print("Aucune donnee collectee. Instantane non ecrit.")
        return

    FICHIER_SORTIE.write_text(
        json.dumps(donnees, indent=1), encoding="utf-8"
    )

    taille = FICHIER_SORTIE.stat().st_size / 1024
    total = sum(
        len(e["calls"]) + len(e["puts"])
        for t in donnees["tickers"].values()
        for e in t["expiries"].values()
    )

    print(f"Ecrit : {FICHIER_SORTIE} ({taille:.0f} Ko, {total} contrats)")
    print(f"Sous-jacents : {', '.join(donnees['tickers'])}")


if __name__ == "__main__":
    main()
