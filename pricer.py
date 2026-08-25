import numpy as np
from scipy.stats import norm
import yfinance as yf

from datetime import datetime


def calcule_d1_d2(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def black_scholes(S, K, T, r, sigma, option_type):
    """
    Calcule le prix d'une option européenne avec le modèle Black-Scholes.
    """
    d1, d2 = calcule_d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        prix = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        prix = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return prix


def delta(S, K, T, r, sigma, option_type):
    """
    Calcule le delta : sensibilité du prix de l'option à une variation
    de 1 unité du prix du sous-jacent.
    """
    d1, _ = calcule_d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1

def gamma(S, K, T, r, sigma):
    """
    Calcule le gamma : sensibilité du delta à une variation
    de 1 unité du prix du sous-jacent. Identique pour call et put.
    """
    d1, _ = calcule_d1_d2(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))

def vega(S, K, T, r, sigma):
    """
    Calcule le vega : sensibilité du prix de l'option à une variation
    de 1 point de volatilité (ex: 20% -> 21%). Identique pour call et put.
    """
    d1, _ = calcule_d1_d2(S, K, T, r, sigma)
    return S * norm.pdf(d1) * np.sqrt(T) / 100

def theta(S, K, T, r, sigma, option_type):
    """
    Calcule le theta : perte de valeur de l'option chaque jour qui passe,
    toutes choses égales par ailleurs. Exprimé par jour (annuel / 365).
    """
    d1, d2 = calcule_d1_d2(S, K, T, r, sigma)
    terme_commun = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))

    if option_type == "call":
        theta_annuel = terme_commun - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        theta_annuel = terme_commun + r * K * np.exp(-r * T) * norm.cdf(-d2)

    return theta_annuel / 365

def rho(S, K, T, r, sigma, option_type):
    """
    Calcule le rho : sensibilité du prix de l'option à une variation
    de 1 point de taux sans risque (ex: 3% -> 4%).
    """
    d1, d2 = calcule_d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        return K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100

def monte_carlo_pricer(S, K, T, r, sigma, option_type, nb_simulations=100000):
    """
    Estime le prix d'une option europeenne par simulation Monte Carlo.
    """
    np.random.seed(42)
    Z = np.random.standard_normal(nb_simulations)
    S_T = S * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)

    if option_type == "call":
        payoffs = np.maximum(S_T - K, 0)
    else:
        payoffs = np.maximum(K - S_T, 0)

    prix_estime = np.exp(-r * T) * np.mean(payoffs)
    return prix_estime

    
ticker = yf.Ticker("AAPL")
data = ticker.history(period="1y")

spot_reel = data["Close"].iloc[-1]

rendements = np.log(data["Close"] / data["Close"].shift(1))
vol_historique = rendements.std() * np.sqrt(252)

print("Prix actuel d'Apple (spot réel) :", spot_reel)
print("Volatilité historique annualisée :", vol_historique)

S = spot_reel
K = round(spot_reel)
T = 1
r = 0.03
sigma = vol_historique

    


prix_call = black_scholes(S, K, T, r, sigma, "call")
prix_put = black_scholes(S, K, T, r, sigma, "put")
print("Prix du call :", prix_call)
print("Prix du put :", prix_put)

parite_ok = np.isclose(prix_call - prix_put, S - K * np.exp(-r * T))
print("Parité call-put respectée :", parite_ok)

delta_call = delta(S, K, T, r, sigma, "call")
delta_put = delta(S, K, T, r, sigma, "put")
print("Delta du call :", delta_call)
print("Delta du put :", delta_put)
gamma_option = gamma(S, K, T, r, sigma)
print("Gamma :", gamma_option)
vega_option = vega(S, K, T, r, sigma)
print("Vega :", vega_option)
theta_call = theta(S, K, T, r, sigma, "call")
theta_put = theta(S, K, T, r, sigma, "put")
print("Theta du call (par jour) :", theta_call)
print("Theta du put (par jour) :", theta_put)

rho_call = rho(S, K, T, r, sigma, "call")
rho_put = rho(S, K, T, r, sigma, "put")
print("Rho du call :", rho_call)
print("Rho du put :", rho_put)

rho_check = np.isclose(rho_call - rho_put, K * T * np.exp(-r * T) / 100)
print("Relation Rho call/put respectée :", rho_check)

dates_disponibles = ticker.options
print("Dates d'expiration disponibles :", dates_disponibles)

date_choisie = dates_disponibles[7]
aujourdhui = datetime.today()
date_expiration = datetime.strptime(date_choisie, "%Y-%m-%d")
jours_restants = (date_expiration - aujourdhui).days
T_reel = jours_restants / 365

print("Date d'expiration choisie :", date_choisie)
print("Jours restants avant expiration :", jours_restants)
print("T réel (en années) :", T_reel)

chaine = ticker.option_chain(date_choisie)
calls = chaine.calls

calls["ecart"] = (calls["strike"] - spot_reel).abs()
option_proche = calls.sort_values("ecart").iloc[0]

K_reel = option_proche["strike"]
prix_marche = option_proche["lastPrice"]

print("Strike réel le plus proche du spot :", K_reel)
print("Prix du call coté sur le marché :", prix_marche)

prix_theorique = black_scholes(S, K_reel, T_reel, r, sigma, "call")
print("Prix théorique (notre modèle) :", prix_theorique)

ecart_prix = prix_marche - prix_theorique
print("Écart entre marché et modèle :", ecart_prix)

prix_call_mc = monte_carlo_pricer(S, K_reel, T_reel, r, sigma, "call")
print("Prix du call (Monte Carlo) :", prix_call_mc)
print("Prix du call (Black-Scholes) :", prix_theorique)

ecart_mc = abs(prix_call_mc - prix_theorique)
print("Ecart Monte Carlo vs Black-Scholes :", ecart_mc)







