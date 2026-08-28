"""
Moteur de pricing d'options europeennes et americaines.

Contient les modeles (Black-Scholes, Monte Carlo, arbre binomial CRR),
les grecques, l'inversion en volatilite implicite et une simulation
de delta-hedging.

Ce module ne depend ni de Streamlit ni d'aucune source de donnees : il
recoit des nombres et renvoie des nombres. L'acquisition des donnees de
marche est traitee dans donnees.py.

Lancer directement (python3 pricer.py) execute une demonstration.
"""

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Black-Scholes et grecques
# ---------------------------------------------------------------------------

def calcule_d1_d2(S, K, T, r, sigma):
    """Termes intermediaires d1 et d2 de la formule de Black-Scholes."""
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


def black_scholes(S, K, T, r, sigma, option_type):
    """Prix d'une option europeenne par la formule fermee de Black-Scholes."""
    d1, d2 = calcule_d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        prix = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        prix = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return prix


def delta(S, K, T, r, sigma, option_type):
    """Sensibilite du prix a une variation de 1 unite du sous-jacent."""
    d1, _ = calcule_d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1


def gamma(S, K, T, r, sigma):
    """Sensibilite du delta au sous-jacent. Identique pour call et put."""
    d1, _ = calcule_d1_d2(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))


def vega(S, K, T, r, sigma):
    """Sensibilite a 1 point de volatilite (20% -> 21%). Call = put."""
    d1, _ = calcule_d1_d2(S, K, T, r, sigma)
    return S * norm.pdf(d1) * np.sqrt(T) / 100


def theta(S, K, T, r, sigma, option_type):
    """Perte de valeur par jour calendaire, toutes choses egales par ailleurs."""
    d1, d2 = calcule_d1_d2(S, K, T, r, sigma)
    terme_commun = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))

    if option_type == "call":
        theta_annuel = terme_commun - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        theta_annuel = terme_commun + r * K * np.exp(-r * T) * norm.cdf(-d2)

    return theta_annuel / 365


def rho(S, K, T, r, sigma, option_type):
    """Sensibilite a 1 point de taux sans risque (3% -> 4%)."""
    _, d2 = calcule_d1_d2(S, K, T, r, sigma)

    if option_type == "call":
        return K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100


# ---------------------------------------------------------------------------
# Methodes numeriques
# ---------------------------------------------------------------------------

def monte_carlo_pricer(S, K, T, r, sigma, option_type, nb_simulations=100000,
                       seed=42):
    """Estime le prix d'une option europeenne par simulation Monte Carlo.

    Utilise un generateur local (default_rng) plutot que np.random.seed,
    qui modifierait l'etat aleatoire global du programme appelant.
    """
    rng = np.random.default_rng(seed)
    Z = rng.standard_normal(nb_simulations)
    S_T = S * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)

    if option_type == "call":
        payoffs = np.maximum(S_T - K, 0)
    else:
        payoffs = np.maximum(K - S_T, 0)

    return np.exp(-r * T) * np.mean(payoffs)


def binomial_tree(S, K, T, r, sigma, option_type, exercise_type="europeenne",
                  N=500):
    """Price une option avec un arbre binomial Cox-Ross-Rubinstein.

    exercise_type : "europeenne" ou "americaine". Dans le cas americain,
    on compare a chaque noeud la valeur de continuation au payoff immediat.
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
            prix_noeuds = np.array(
                [S * (u ** j) * (d ** (i - j)) for j in range(i + 1)]
            )
            if option_type == "call":
                payoff_immediat = np.maximum(prix_noeuds - K, 0)
            else:
                payoff_immediat = np.maximum(K - prix_noeuds, 0)
            valeurs = np.maximum(valeurs, payoff_immediat)

    return valeurs[0]


# ---------------------------------------------------------------------------
# Volatilite implicite
# ---------------------------------------------------------------------------

def borne_arbitrage(S, K, T, r, option_type):
    """Valeur minimale d'une option europeenne (valeur intrinseque actualisee).

    En dessous de cette borne, il existerait une opportunite d'arbitrage :
    aucune volatilite ne peut expliquer un tel prix.
    """
    if option_type == "call":
        return max(S - K * np.exp(-r * T), 0.0)
    return max(K * np.exp(-r * T) - S, 0.0)


def volatilite_implicite_newton(prix_marche, S, K, T, r, option_type,
                                sigma_init=0.3, tolerance=1e-8,
                                max_iterations=100):
    """Recherche la volatilite implicite par la methode de Newton-Raphson.

    Renvoie None si la methode ne converge pas ou si le probleme est mal
    pose (prix sous la borne d'arbitrage, ou vega trop faible pour que la
    volatilite soit identifiable numeriquement).
    """
    if prix_marche <= borne_arbitrage(S, K, T, r, option_type) + 1e-10:
        return None

    sigma = sigma_init

    for _ in range(max_iterations):
        d1, _ = calcule_d1_d2(S, K, T, r, sigma)
        vega_brut = S * norm.pdf(d1) * np.sqrt(T)

        # Sans vega, le prix ne reagit plus a sigma : rien a inverser.
        if vega_brut < 1e-8:
            return None

        ecart = black_scholes(S, K, T, r, sigma, option_type) - prix_marche

        # Tolerance relative au prix : un ecart de 1e-6 n'a pas le meme sens
        # sur une option a 0.01 et sur une option a 80.
        if abs(ecart) < tolerance * max(1.0, abs(prix_marche)):
            return sigma

        sigma = sigma - ecart / vega_brut

        if sigma <= 0 or sigma > 5:
            return None

    return None


def volatilite_implicite(prix_marche, S, K, T, r, option_type):
    """Volatilite implicite : Newton-Raphson, avec Brent en filet de securite.

    Newton est rapide mais diverge quand le vega approche zero (options tres
    dans ou hors de la monnaie). Brent ne depend pas de la derivee et trouve
    la solution dans un intervalle donne, au prix de plus d'iterations.

    Renvoie None quand la volatilite n'est pas identifiable.
    """
    # Sans valeur temps, le prix ne depend plus du tout de sigma : n'importe
    # quelle volatilite redonne le meme prix. Inutile d'essayer d'inverser.
    if prix_marche <= borne_arbitrage(S, K, T, r, option_type) + 1e-10:
        return None

    sigma = volatilite_implicite_newton(prix_marche, S, K, T, r, option_type)

    if sigma is not None:
        return sigma

    def ecart_prix(sigma_test):
        return black_scholes(S, K, T, r, sigma_test, option_type) - prix_marche

    try:
        return brentq(ecart_prix, 1e-6, 5)
    except ValueError:
        # Pas de changement de signe sur l'intervalle : pas de solution.
        return None


def calcule_smile(calls, puts, spot, r, T):
    """Smile de volatilite implicite a partir de contrats cotes.

    calls et puts sont des listes de dictionnaires contenant les cles
    "strike" et "lastPrice". Cette fonction ne fait aucun appel reseau :
    elle recoit les donnees deja acquises, ce qui la rend testable et
    independante de leur provenance.

    Seuls les contrats hors de la monnaie sont retenus (puts sous le spot,
    calls au-dessus) : ce sont les plus liquides, donc les plus fiables.

    Renvoie (strikes, vols), tries par strike croissant.
    """
    if T <= 0:
        return [], []

    strikes = []
    vols = []

    for contrats, type_option in [(puts, "put"), (calls, "call")]:
        for contrat in contrats:
            K = contrat["strike"]
            prix = contrat["lastPrice"]

            # Ecarte les contrats sans transaction recente.
            if prix <= 0.1:
                continue

            hors_monnaie = (
                (type_option == "put" and spot * 0.85 < K <= spot)
                or (type_option == "call" and spot < K < spot * 1.15)
            )
            if not hors_monnaie:
                continue

            try:
                vi = volatilite_implicite(prix, spot, K, T, r, type_option)
            except Exception:
                continue

            if vi is not None and 0.01 < vi < 3:
                strikes.append(K)
                vols.append(vi)

    points_tries = sorted(zip(strikes, vols))

    return [p[0] for p in points_tries], [p[1] for p in points_tries]


# ---------------------------------------------------------------------------
# Delta-hedging
# ---------------------------------------------------------------------------

def simule_delta_hedging(S, K, T, r, sigma, n_rebalancements, seed=None):
    """Simule la couverture en delta d'un call vendu sur une trajectoire.

    Le vendeur encaisse la prime Black-Scholes, achete delta actions, puis
    reajuste a chaque pas. Le solde de tresorerie porte interet au taux
    sans risque. Le P&L final mesure l'erreur de couverture due au fait
    que le reajustement est discret et non continu.
    """
    rng = np.random.default_rng(seed)

    dt = T / n_rebalancements

    # Trajectoire du sous-jacent (mouvement brownien geometrique)
    chocs = rng.standard_normal(n_rebalancements)
    prix = np.zeros(n_rebalancements + 1)
    prix[0] = S

    for i in range(n_rebalancements):
        prix[i + 1] = prix[i] * np.exp(
            (r - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * chocs[i]
        )

    prime = black_scholes(S, K, T, r, sigma, "call")

    delta_courant = delta(S, K, T, r, sigma, "call")
    tresorerie = prime - delta_courant * S

    positions = np.zeros(n_rebalancements + 1)
    positions[0] = delta_courant

    for i in range(1, n_rebalancements):
        temps_restant = T - i * dt
        tresorerie = tresorerie * np.exp(r * dt)

        nouveau_delta = delta(prix[i], K, temps_restant, r, sigma, "call")
        tresorerie = tresorerie - (nouveau_delta - delta_courant) * prix[i]

        delta_courant = nouveau_delta
        positions[i] = delta_courant

    # Denouement a l'echeance
    tresorerie = tresorerie * np.exp(r * dt)
    positions[-1] = delta_courant

    valeur_actions = delta_courant * prix[-1]
    payoff_du_client = max(prix[-1] - K, 0)
    pnl = tresorerie + valeur_actions - payoff_du_client

    return {
        "prix": prix,
        "positions": positions,
        "prime": prime,
        "pnl": pnl,
        "spot_final": prix[-1],
        "payoff": payoff_du_client,
    }


# ---------------------------------------------------------------------------
# Demonstration sur donnees reelles
#
# Les imports lourds restent ici : ils ne servent qu'a cette demonstration,
# et app.py n'a pas a les charger.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go

    import donnees

    SYMBOLE = "AAPL"
    r = 0.03

    spot_reel, vol_historique = donnees.charger_prix_et_volatilite(SYMBOLE)

    if spot_reel is None:
        print("Donnees de marche indisponibles.")
        raise SystemExit(1)

    print("Prix actuel (spot reel) :", spot_reel)
    print("Volatilite historique annualisee :", vol_historique)

    S = spot_reel
    K = round(spot_reel)
    T = 1
    sigma = vol_historique

    # --- Prix et parite call-put ---
    prix_call = black_scholes(S, K, T, r, sigma, "call")
    prix_put = black_scholes(S, K, T, r, sigma, "put")
    print("Prix du call :", prix_call)
    print("Prix du put :", prix_put)
    print("Parite call-put respectee :",
          np.isclose(prix_call - prix_put, S - K * np.exp(-r * T)))

    # --- Grecques ---
    print("Delta du call :", delta(S, K, T, r, sigma, "call"))
    print("Delta du put :", delta(S, K, T, r, sigma, "put"))
    print("Gamma :", gamma(S, K, T, r, sigma))
    print("Vega :", vega(S, K, T, r, sigma))
    print("Theta du call (par jour) :", theta(S, K, T, r, sigma, "call"))
    print("Theta du put (par jour) :", theta(S, K, T, r, sigma, "put"))

    rho_call = rho(S, K, T, r, sigma, "call")
    rho_put = rho(S, K, T, r, sigma, "put")
    print("Rho du call :", rho_call)
    print("Rho du put :", rho_put)
    print("Relation Rho call/put respectee :",
          np.isclose(rho_call - rho_put, K * T * np.exp(-r * T) / 100))

    # --- Echeance reelle ---
    echeances, source = donnees.charger_echeances(SYMBOLE)
    print(f"\nEcheances disponibles ({source}) :", echeances)

    if not echeances:
        print("Aucune echeance exploitable, fin de la demonstration.")
        raise SystemExit(0)

    date_choisie = echeances[min(2, len(echeances) - 1)]
    T_reel = donnees.annees_jusqua(date_choisie)

    print("Echeance choisie :", date_choisie)
    print("T reel (en annees) :", T_reel)

    calls, puts, source_chaine = donnees.charger_chaine(SYMBOLE, date_choisie)
    print(f"Chaine recuperee ({source_chaine}) :",
          f"{len(calls)} calls, {len(puts)} puts")

    # --- Comparaison au prix cote (strike le plus proche du spot) ---
    if calls:
        option_proche = min(calls, key=lambda c: abs(c["strike"] - spot_reel))
        K_reel = option_proche["strike"]
        prix_marche = option_proche["lastPrice"]

        print("Strike le plus proche du spot :", K_reel)
        print("Prix du call cote :", prix_marche)

        prix_theorique = black_scholes(S, K_reel, T_reel, r, sigma, "call")
        print("Prix theorique (notre modele) :", prix_theorique)
        print("Ecart entre marche et modele :", prix_marche - prix_theorique)

        # --- Convergence des methodes ---
        prix_mc = monte_carlo_pricer(S, K_reel, T_reel, r, sigma, "call")
        prix_bin = binomial_tree(S, K_reel, T_reel, r, sigma, "call", N=500)
        print("Ecart Monte Carlo vs Black-Scholes :",
              abs(prix_mc - prix_theorique))
        print("Ecart arbre binomial vs Black-Scholes :",
              abs(prix_bin - prix_theorique))

        # --- Exercice anticipe ---
        put_eu = binomial_tree(S, K_reel, T_reel, r, sigma, "put",
                               exercise_type="europeenne", N=500)
        put_us = binomial_tree(S, K_reel, T_reel, r, sigma, "put",
                               exercise_type="americaine", N=500)
        print("Prime d'exercice anticipe (put) :", put_us - put_eu)

        # --- Volatilite implicite ---
        vol_implicite = volatilite_implicite(prix_marche, S, K_reel, T_reel,
                                             r, "call")
        print("Volatilite implicite :", vol_implicite)
        print("Volatilite historique :", sigma)

        if vol_implicite is not None:
            print("Reprice avec la vol implicite :",
                  black_scholes(S, K_reel, T_reel, r, vol_implicite, "call"))

    # --- Smile ---
    # Sur donnees figees, on utilise le spot enregistre avec elles.
    spot_reference = spot_reel
    if source_chaine == donnees.SNAPSHOT:
        spot_reference = donnees.spot_snapshot(SYMBOLE) or spot_reel

    strikes_smile, vols_smile = calcule_smile(calls, puts, spot_reference,
                                              r, T_reel)
    print("\nNombre de points pour le smile :", len(strikes_smile))

    if strikes_smile:
        plt.figure(figsize=(10, 6))
        plt.plot(strikes_smile, vols_smile, marker="o", linestyle="-")
        plt.axvline(spot_reference, color="red", linestyle="--", label="Spot")
        plt.xlabel("Strike")
        plt.ylabel("Volatilite implicite")
        plt.title(f"Smile de volatilite - {SYMBOLE} - echeance {date_choisie}")
        plt.legend()
        plt.grid(True)
        plt.savefig("smile_matplotlib.png", dpi=150)
        plt.show()

    # --- Surface ---
    x_moneyness = []
    y_jours = []
    z_vols = []

    for date_exp in echeances[:8]:
        c, p, src = donnees.charger_chaine(SYMBOLE, date_exp)
        T_e = donnees.annees_jusqua(date_exp)

        ref = spot_reel
        if src == donnees.SNAPSHOT:
            ref = donnees.spot_snapshot(SYMBOLE) or spot_reel

        ks, vs = calcule_smile(c, p, ref, r, T_e)

        if len(ks) < 5:
            continue

        for k, v in zip(ks, vs):
            x_moneyness.append(k / ref)
            y_jours.append(T_e * 365)
            z_vols.append(v)

    print("Nombre total de points pour la surface :", len(z_vols))

    if len(z_vols) >= 20:
        figure_3d = go.Figure(data=[go.Mesh3d(
            x=x_moneyness, y=y_jours, z=z_vols,
            intensity=z_vols, colorscale="Viridis", opacity=0.9,
        )])
        figure_3d.update_layout(
            title=f"Surface de volatilite implicite - {SYMBOLE}",
            scene=dict(
                xaxis_title="Moneyness (Strike / Spot)",
                yaxis_title="Jours avant expiration",
                zaxis_title="Volatilite implicite",
            ),
        )
        figure_3d.write_html("surface_volatilite.html")
        figure_3d.show()

    # --- Delta-hedging : loi en 1/sqrt(n) ---
    print("\n--- Simulation de delta-hedging ---")
    print("(300 trajectoires par frequence de reajustement)")
    print(f"{'Pas':>6} | {'P&L moyen':>10} | {'Ecart-type':>10} | {'x sqrt(n)':>10}")

    for n in [10, 50, 250, 1000]:
        pnls = [
            simule_delta_hedging(100, 100, 1, 0.03, 0.20, n, seed=i)["pnl"]
            for i in range(300)
        ]
        ecart_type = np.std(pnls)
        print(f"{n:6d} | {np.mean(pnls):+10.4f} | {ecart_type:10.4f} | "
              f"{ecart_type * np.sqrt(n):10.4f}")

        