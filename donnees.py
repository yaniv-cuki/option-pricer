"""
Couche d'acces aux donnees de marche.

Isole l'application de la source des donnees. Chaque fonction tente d'abord
l'acces en direct via yfinance, puis retombe sur l'instantane local si le
direct echoue, et indique toujours quelle source a ete utilisee.

Yahoo Finance limite les requetes venant des serveurs cloud sur les endpoints
proteges par jeton (HTTP 429). Les prix passent, les chaines d'options non.
D'ou ce repli, qui garantit que l'application reste utilisable en ligne.
"""

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
import yfinance as yf

FICHIER_SNAPSHOT = Path(__file__).parent / "snapshot_options.json"

# Valeurs possibles pour la source d'une donnee
LIVE = "live"
SNAPSHOT = "snapshot"
AUCUNE = "aucune"


@lru_cache(maxsize=1)
def _snapshot():
    """Charge l'instantane une seule fois par execution."""
    if not FICHIER_SNAPSHOT.exists():
        return {"genere_le": None, "tickers": {}}

    try:
        return json.loads(FICHIER_SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        return {"genere_le": None, "tickers": {}}


def date_snapshot():
    """Date de generation de l'instantane, ou None s'il n'existe pas."""
    return _snapshot().get("genere_le")


def tickers_snapshot():
    """Sous-jacents couverts par l'instantane."""
    return sorted(_snapshot().get("tickers", {}))


def annees_jusqua(date_expiration):
    """Temps restant jusqu'a une echeance, exprime en annees."""
    date_exp = datetime.strptime(date_expiration, "%Y-%m-%d")
    jours = (date_exp - datetime.today()).days
    return max(jours, 0) / 365


# ---------------------------------------------------------------------------
# Prix du sous-jacent : toujours en direct, l'endpoint n'est pas limite
# ---------------------------------------------------------------------------

def charger_prix_et_volatilite(symbole):
    """Spot courant et volatilite historique annualisee sur 1 an.

    Le spot est pris sur la serie intraday quand elle existe, pour rester
    coherent avec le bandeau de cotation.
    """
    try:
        tk = yf.Ticker(symbole)
        historique = tk.history(period="1y")

        if historique.empty:
            return None, None

        rendements = np.log(historique["Close"] / historique["Close"].shift(1))
        volatilite = float(rendements.std() * np.sqrt(252))

        intraday = charger_intraday(symbole)
        if intraday is not None:
            spot = intraday["dernier"]
        else:
            spot = float(historique["Close"].iloc[-1])

        return spot, volatilite
    except Exception:
        return None, None


def charger_intraday(symbole):
    """Serie intraday et variation depuis la cloture precedente."""
    try:
        tk = yf.Ticker(symbole)
        intraday = tk.history(period="1d", interval="5m")
        recent = tk.history(period="5d")

        if intraday.empty or len(recent) < 2:
            return None

        dernier = float(intraday["Close"].iloc[-1])
        cloture_precedente = float(recent["Close"].iloc[-2])
        variation = dernier - cloture_precedente

        return {
            "dernier": dernier,
            "variation": variation,
            "variation_pct": variation / cloture_precedente * 100,
            "serie": [float(x) for x in intraday["Close"].tolist()],
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Chaines d'options : direct si possible, instantane sinon
# ---------------------------------------------------------------------------

def charger_echeances(symbole):
    """Dates d'expiration disponibles.

    Renvoie (liste_dates, source).
    """
    try:
        dates = list(yf.Ticker(symbole).options)
        if dates:
            return dates, LIVE
    except Exception:
        pass

    fiche = _snapshot()["tickers"].get(symbole.upper())

    if fiche:
        # On ecarte les echeances de l'instantane deja expirees.
        dates = [d for d in fiche["expiries"] if annees_jusqua(d) > 0]
        if dates:
            return sorted(dates), SNAPSHOT

    return [], AUCUNE


def charger_chaine(symbole, date_expiration):
    """Contrats cotes pour une echeance donnee.

    Renvoie (calls, puts, source), ou calls et puts sont des listes de
    dictionnaires contenant les cles "strike" et "lastPrice".
    """
    try:
        chaine = yf.Ticker(symbole).option_chain(date_expiration)

        calls = [
            {"strike": float(l["strike"]), "lastPrice": float(l["lastPrice"])}
            for _, l in chaine.calls.iterrows()
        ]
        puts = [
            {"strike": float(l["strike"]), "lastPrice": float(l["lastPrice"])}
            for _, l in chaine.puts.iterrows()
        ]

        if calls or puts:
            return calls, puts, LIVE
    except Exception:
        pass

    fiche = _snapshot()["tickers"].get(symbole.upper())

    if fiche and date_expiration in fiche["expiries"]:
        echeance = fiche["expiries"][date_expiration]
        return echeance["calls"], echeance["puts"], SNAPSHOT

    return [], [], AUCUNE


def spot_snapshot(symbole):
    """Spot enregistre dans l'instantane, ou None.

    Sert de reference pour la moneyness quand on travaille sur des donnees
    d'options figees : utiliser le spot du jour avec des prix d'options
    anciens fausserait les volatilites implicites.
    """
    fiche = _snapshot()["tickers"].get(symbole.upper())
    return fiche["spot"] if fiche else None
