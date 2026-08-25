import numpy as np
from scipy.stats import norm
import yfinance as yf
from datetime import datetime
from scipy.optimize import brentq
import matplotlib.pyplot as plt
import plotly.graph_objects as go



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

def binomial_tree(S, K, T, r, sigma, option_type, exercise_type="europeenne", N=500):
    """
    Price une option avec un arbre binomial CRR.
    exercise_type : "europeenne" ou "americaine".
    """
    dt = T / N
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(r * dt) - d) / (u - d)
    discount = np.exp(-r * dt)

    prix_finaux = np.array([S * (u ** j) * (d ** (N - j)) for j in range(N + 1)])

    if option_type == "call":
        valeurs = np.maximum(prix_finaux - K, 0)
    else:
        valeurs = np.maximum(K - prix_finaux, 0)

    for i in range(N - 1, -1, -1):
        valeurs = discount * (p * valeurs[1:i + 2] + (1 - p) * valeurs[0:i + 1])

        if exercise_type == "americaine":
            prix_noeuds = np.array([S * (u ** j) * (d ** (i - j)) for j in range(i + 1)])
            if option_type == "call":
                payoff_immediat = np.maximum(prix_noeuds - K, 0)
            else:
                payoff_immediat = np.maximum(K - prix_noeuds, 0)
            valeurs = np.maximum(valeurs, payoff_immediat)

    return valeurs[0]

def volatilite_implicite_newton(prix_marche, S, K, T, r, option_type, sigma_init=0.3, tolerance=1e-6, max_iterations=100):
    """
    Recherche la volatilite implicite par la methode de Newton-Raphson.
    Renvoie None si la methode ne converge pas.
    """
    sigma = sigma_init

    for i in range(max_iterations):
        prix_estime = black_scholes(S, K, T, r, sigma, option_type)
        ecart = prix_estime - prix_marche

        if abs(ecart) < tolerance:
            return sigma

        d1, _ = calcule_d1_d2(S, K, T, r, sigma)
        vega_brut = S * norm.pdf(d1) * np.sqrt(T)

        if vega_brut < 1e-8:
            return None

        sigma = sigma - ecart / vega_brut

    return None


def volatilite_implicite(prix_marche, S, K, T, r, option_type):
    """
    Calcule la volatilite implicite. Essaie Newton-Raphson d'abord (rapide),
    puis scipy.optimize.brentq en filet de securite si Newton-Raphson diverge.
    """
    sigma = volatilite_implicite_newton(prix_marche, S, K, T, r, option_type)

    if sigma is not None:
        return sigma

    def ecart_prix(sigma_test):
        return black_scholes(S, K, T, r, sigma_test, option_type) - prix_marche

    return brentq(ecart_prix, 1e-6, 5)

def calcule_smile(ticker_obj, date_expiration_str, spot, r):
    """
    Calcule le smile de volatilite implicite pour une echeance donnee.
    Utilise les puts OTM sous le spot et les calls OTM au-dessus.
    Renvoie (liste_strikes, liste_vols, T).
    """
    aujourdhui = datetime.today()
    date_exp = datetime.strptime(date_expiration_str, "%Y-%m-%d")
    jours = (date_exp - aujourdhui).days

    if jours <= 0:
        return [], [], 0

    T = jours / 365
    chaine_locale = ticker_obj.option_chain(date_expiration_str)

    puts_otm = chaine_locale.puts[
        (chaine_locale.puts["lastPrice"] > 0.1)
        & (chaine_locale.puts["strike"] > spot * 0.85)
        & (chaine_locale.puts["strike"] <= spot)
    ]

    calls_otm = chaine_locale.calls[
        (chaine_locale.calls["lastPrice"] > 0.1)
        & (chaine_locale.calls["strike"] > spot)
        & (chaine_locale.calls["strike"] < spot * 1.15)
    ]

    strikes = []
    vols = []

    for index, ligne in puts_otm.iterrows():
        try:
            vi = volatilite_implicite(ligne["lastPrice"], spot, ligne["strike"], T, r, "put")
            if vi is not None and 0.01 < vi < 3:
                strikes.append(ligne["strike"])
                vols.append(vi)
        except Exception:
            continue

    for index, ligne in calls_otm.iterrows():
        try:
            vi = volatilite_implicite(ligne["lastPrice"], spot, ligne["strike"], T, r, "call")
            if vi is not None and 0.01 < vi < 3:
                strikes.append(ligne["strike"])
                vols.append(vi)
        except Exception:
            continue

    points_tries = sorted(zip(strikes, vols))
    strikes = [p[0] for p in points_tries]
    vols = [p[1] for p in points_tries]

    return strikes, vols, T




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

prix_call_binomial = binomial_tree(S, K_reel, T_reel, r, sigma, "call", exercise_type="europeenne", N=500)
print("Prix du call (arbre binomial) :", prix_call_binomial)
print("Prix du call (Black-Scholes) :", prix_theorique)

ecart_binomial = abs(prix_call_binomial - prix_theorique)
print("Ecart arbre binomial vs Black-Scholes :", ecart_binomial)

prix_put_europeen = binomial_tree(S, K_reel, T_reel, r, sigma, "put", exercise_type="europeenne", N=500)
prix_put_americain = binomial_tree(S, K_reel, T_reel, r, sigma, "put", exercise_type="americaine", N=500)

print("Prix du put europeen (arbre) :", prix_put_europeen)
print("Prix du put americain (arbre) :", prix_put_americain)
print("Prime d'exercice anticipe (put) :", prix_put_americain - prix_put_europeen)

vol_implicite = volatilite_implicite(prix_marche, S, K_reel, T_reel, r, "call")
print("Volatilite implicite (deduite du marche) :", vol_implicite)
print("Volatilite historique (calculee plus tot) :", sigma)

prix_verif = black_scholes(S, K_reel, T_reel, r, vol_implicite, "call")
print("Prix Black-Scholes avec cette vol implicite :", prix_verif)
print("Prix reel du marche :", prix_marche)

puts = chaine.puts

puts_otm = puts[
    (puts["lastPrice"] > 0.1)
    & (puts["strike"] > spot_reel * 0.85)
    & (puts["strike"] <= spot_reel)
]

calls_otm = calls[
    (calls["lastPrice"] > 0.1)
    & (calls["strike"] > spot_reel)
    & (calls["strike"] < spot_reel * 1.15)
]

strikes_smile = []
vols_smile = []

for index, ligne in puts_otm.iterrows():
    try:
        vi = volatilite_implicite(ligne["lastPrice"], S, ligne["strike"], T_reel, r, "put")
        if vi is not None and 0.01 < vi < 3:
            strikes_smile.append(ligne["strike"])
            vols_smile.append(vi)
    except Exception:
        continue

for index, ligne in calls_otm.iterrows():
    try:
        vi = volatilite_implicite(ligne["lastPrice"], S, ligne["strike"], T_reel, r, "call")
        if vi is not None and 0.01 < vi < 3:
            strikes_smile.append(ligne["strike"])
            vols_smile.append(vi)
    except Exception:
        continue

points = sorted(zip(strikes_smile, vols_smile))
strikes_smile = [p[0] for p in points]
vols_smile = [p[1] for p in points]

print("Nombre de points calcules pour le smile :", len(strikes_smile))

plt.figure(figsize=(10, 6))
plt.plot(strikes_smile, vols_smile, marker="o", linestyle="-")
plt.axvline(spot_reel, color="red", linestyle="--", label="Spot actuel")
plt.xlabel("Strike")
plt.ylabel("Volatilite implicite")
plt.title("Smile de volatilite - AAPL - echeance " + date_choisie)
plt.legend()
plt.grid(True)
plt.savefig("smile_volatilite.png", dpi=150)
plt.show()

echeances_surface = dates_disponibles[5:12]

x_strikes = []
y_maturites = []
z_vols = []

for date_exp in echeances_surface:
    strikes_e, vols_e, T_e = calcule_smile(ticker, date_exp, spot_reel, r)

    if len(strikes_e) < 5:
        continue

    for k, v in zip(strikes_e, vols_e):
        x_strikes.append(k / spot_reel)
        y_maturites.append(T_e * 365)
        z_vols.append(v)

print("Nombre total de points pour la surface :", len(z_vols))

figure_3d = go.Figure(data=[go.Mesh3d(
    x=x_strikes,
    y=y_maturites,
    z=z_vols,
    intensity=z_vols,
    colorscale="Viridis",
    opacity=0.9
)])

figure_3d.update_layout(
    title="Surface de volatilite implicite - AAPL",
    scene=dict(
        xaxis_title="Moneyness (Strike / Spot)",
        yaxis_title="Jours avant expiration",
        zaxis_title="Volatilite implicite"
    )
)

figure_3d.write_html("surface_volatilite.html")
figure_3d.show()














