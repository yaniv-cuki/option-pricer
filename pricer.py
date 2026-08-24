import numpy as np
from scipy.stats import norm


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

    
S = 100
K = 100
T = 1
r = 0.03
sigma = 0.20

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



