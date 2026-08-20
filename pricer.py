import numpy as np
from scipy.stats import norm
def black_scholes(S, K, T, r, sigma, option_type):
    """
    Calcule le prix d'une option européenne avec le modèle Black-Scholes.
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == "call":
        prix = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        prix = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return prix

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





    

