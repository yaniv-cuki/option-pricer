"""
Suite de tests du moteur de pricing.

Chaque methode est verifiee contre une identite qui doit etre vraie si
l'implementation est correcte, et non contre une valeur attendue notee
a la main.

Lancer :  pytest -v
"""

import numpy as np
import pytest

from pricer import (
    binomial_tree,
    black_scholes,
    calcule_smile,
    delta,
    gamma,
    monte_carlo_pricer,
    rho,
    simule_delta_hedging,
    theta,
    vega,
    volatilite_implicite,
)

# Jeux de parametres couvrant plusieurs regimes : a la monnaie, dans la
# monnaie, hors de la monnaie, echeances courtes et longues, vol faible
# et forte.
CAS = [
    # (S,    K,     T,      r,     sigma)
    (100.0, 100.0, 1.0, 0.03, 0.20),
    (313.0, 313.0, 30 / 365, 0.03, 0.25),
    (250.0, 350.0, 1.5, 0.05, 0.40),
    (50.0, 45.0, 0.25, 0.01, 0.15),
    (100.0, 110.0, 2.0, 0.04, 0.60),
]


# ---------------------------------------------------------------------------
# Black-Scholes
# ---------------------------------------------------------------------------

def test_valeurs_de_reference():
    """Compare a un exemple publie (Hull, Options Futures and Other Derivatives)."""
    call = black_scholes(42, 40, 0.5, 0.1, 0.2, "call")
    put = black_scholes(42, 40, 0.5, 0.1, 0.2, "put")

    assert call == pytest.approx(4.76, abs=0.01)
    assert put == pytest.approx(0.81, abs=0.01)


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_parite_call_put(S, K, T, r, sigma):
    """C - P = S - K*exp(-rT), relation d'arbitrage exacte."""
    call = black_scholes(S, K, T, r, sigma, "call")
    put = black_scholes(S, K, T, r, sigma, "put")

    assert call - put == pytest.approx(S - K * np.exp(-r * T))


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_bornes_arbitrage(S, K, T, r, sigma):
    """Une option vaut au moins sa valeur intrinseque actualisee, et un call
    ne vaut jamais plus que le sous-jacent."""
    call = black_scholes(S, K, T, r, sigma, "call")
    put = black_scholes(S, K, T, r, sigma, "put")

    assert call >= max(S - K * np.exp(-r * T), 0) - 1e-9
    assert call <= S
    assert put >= max(K * np.exp(-r * T) - S, 0) - 1e-9
    assert put <= K * np.exp(-r * T)


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_prix_croissant_en_volatilite(S, K, T, r, sigma):
    """Plus de volatilite ne peut que valoriser une option."""
    for type_option in ["call", "put"]:
        bas = black_scholes(S, K, T, r, sigma, type_option)
        haut = black_scholes(S, K, T, r, sigma * 1.5, type_option)
        assert haut > bas


# ---------------------------------------------------------------------------
# Grecques : comparaison aux derivees numeriques
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_delta_vs_derivee_numerique(S, K, T, r, sigma):
    h = S * 1e-5
    for type_option in ["call", "put"]:
        numerique = (black_scholes(S + h, K, T, r, sigma, type_option)
                     - black_scholes(S - h, K, T, r, sigma, type_option)) / (2 * h)
        assert delta(S, K, T, r, sigma, type_option) == pytest.approx(
            numerique, abs=1e-5
        )


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_gamma_vs_derivee_numerique(S, K, T, r, sigma):
    h = S * 1e-4
    numerique = (delta(S + h, K, T, r, sigma, "call")
                 - delta(S - h, K, T, r, sigma, "call")) / (2 * h)
    assert gamma(S, K, T, r, sigma) == pytest.approx(numerique, abs=1e-6)


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_vega_vs_derivee_numerique(S, K, T, r, sigma):
    h = 1e-5
    numerique = (black_scholes(S, K, T, r, sigma + h, "call")
                 - black_scholes(S, K, T, r, sigma - h, "call")) / (2 * h) / 100
    assert vega(S, K, T, r, sigma) == pytest.approx(numerique, abs=1e-5)


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_rho_vs_derivee_numerique(S, K, T, r, sigma):
    h = 1e-6
    for type_option in ["call", "put"]:
        numerique = (black_scholes(S, K, T, r + h, sigma, type_option)
                     - black_scholes(S, K, T, r - h, sigma, type_option)) / (2 * h) / 100
        assert rho(S, K, T, r, sigma, type_option) == pytest.approx(
            numerique, abs=1e-5
        )


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_theta_vs_derivee_numerique(S, K, T, r, sigma):
    h = 1e-6
    for type_option in ["call", "put"]:
        numerique = -(black_scholes(S, K, T + h, r, sigma, type_option)
                      - black_scholes(S, K, T - h, r, sigma, type_option)) / (2 * h) / 365
        assert theta(S, K, T, r, sigma, type_option) == pytest.approx(
            numerique, abs=1e-6
        )


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_signes_des_grecques(S, K, T, r, sigma):
    """Contraintes de signe qui doivent tenir quels que soient les parametres."""
    assert 0 <= delta(S, K, T, r, sigma, "call") <= 1
    assert -1 <= delta(S, K, T, r, sigma, "put") <= 0
    assert gamma(S, K, T, r, sigma) > 0
    assert vega(S, K, T, r, sigma) > 0
    assert rho(S, K, T, r, sigma, "call") > 0
    assert rho(S, K, T, r, sigma, "put") < 0


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_identite_rho(S, K, T, r, sigma):
    """rho_call - rho_put = K*T*exp(-rT), consequence de la parite."""
    ecart = rho(S, K, T, r, sigma, "call") - rho(S, K, T, r, sigma, "put")
    assert ecart == pytest.approx(K * T * np.exp(-r * T) / 100)


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_gamma_et_vega_identiques_call_put(S, K, T, r, sigma):
    """Gamma et vega ne dependent pas du type d'option."""
    h = S * 1e-4
    gamma_put = (delta(S + h, K, T, r, sigma, "put")
                 - delta(S - h, K, T, r, sigma, "put")) / (2 * h)
    assert gamma(S, K, T, r, sigma) == pytest.approx(gamma_put, abs=1e-6)


# ---------------------------------------------------------------------------
# Convergence des methodes numeriques
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_monte_carlo_converge(S, K, T, r, sigma):
    """L'estimation Monte Carlo doit rester proche de la formule fermee."""
    for type_option in ["call", "put"]:
        reference = black_scholes(S, K, T, r, sigma, type_option)
        estimation = monte_carlo_pricer(S, K, T, r, sigma, type_option)
        # Tolerance relative au prix : le bruit d'echantillonnage est
        # proportionnel a l'echelle de l'option.
        assert estimation == pytest.approx(reference, rel=0.02, abs=0.05)


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_binomial_converge(S, K, T, r, sigma):
    """L'arbre binomial est deterministe : il doit coller de tres pres."""
    for type_option in ["call", "put"]:
        reference = black_scholes(S, K, T, r, sigma, type_option)
        arbre = binomial_tree(S, K, T, r, sigma, type_option, N=500)
        assert arbre == pytest.approx(reference, rel=0.005, abs=0.01)


def test_binomial_precision_croit_avec_N():
    """Augmenter le nombre de pas doit rapprocher l'arbre de Black-Scholes."""
    S, K, T, r, sigma = 100, 100, 1, 0.03, 0.20
    reference = black_scholes(S, K, T, r, sigma, "call")

    grossier = abs(binomial_tree(S, K, T, r, sigma, "call", N=20) - reference)
    fin = abs(binomial_tree(S, K, T, r, sigma, "call", N=500) - reference)

    assert fin < grossier


# ---------------------------------------------------------------------------
# Exercice anticipe
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_put_americain_vaut_au_moins_l_europeen(S, K, T, r, sigma):
    """Un droit supplementaire ne peut pas reduire la valeur."""
    europeen = binomial_tree(S, K, T, r, sigma, "put",
                             exercise_type="europeenne", N=500)
    americain = binomial_tree(S, K, T, r, sigma, "put",
                              exercise_type="americaine", N=500)
    assert americain >= europeen - 1e-9


@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_call_americain_egale_europeen_sans_dividende(S, K, T, r, sigma):
    """Sans dividende, exercer un call par anticipation n'est jamais optimal."""
    europeen = binomial_tree(S, K, T, r, sigma, "call",
                             exercise_type="europeenne", N=500)
    americain = binomial_tree(S, K, T, r, sigma, "call",
                              exercise_type="americaine", N=500)
    assert americain == pytest.approx(europeen, abs=1e-8)


def test_prime_exercice_anticipe_significative_put_profond():
    """Sur un put tres dans la monnaie et longue echeance, la prime doit
    devenir economiquement visible."""
    europeen = binomial_tree(250, 350, 550 / 365, 0.03, 0.25, "put",
                             exercise_type="europeenne", N=500)
    americain = binomial_tree(250, 350, 550 / 365, 0.03, 0.25, "put",
                              exercise_type="americaine", N=500)
    assert (americain / europeen - 1) > 0.05


# ---------------------------------------------------------------------------
# Volatilite implicite
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("S,K,T,r,sigma", CAS)
def test_volatilite_implicite_aller_retour(S, K, T, r, sigma):
    """Repricer avec la vol implicite doit redonner le prix de depart."""
    for type_option in ["call", "put"]:
        prix = black_scholes(S, K, T, r, sigma, type_option)
        implicite = volatilite_implicite(prix, S, K, T, r, type_option)

        assert implicite is not None
        assert implicite == pytest.approx(sigma, abs=1e-5)
        assert black_scholes(S, K, T, r, implicite, type_option) == pytest.approx(
            prix, abs=1e-6
        )


def test_volatilite_implicite_renvoie_none_si_non_identifiable():
    """Sans valeur temps, aucune volatilite n'explique le prix : on renvoie
    None plutot qu'un chiffre arbitraire."""
    # Call tres dans la monnaie, echeance courte : le prix est colle a la
    # borne d'arbitrage, le vega est nul.
    prix = black_scholes(100, 20, 0.05, 0.03, 0.20, "call")
    assert volatilite_implicite(prix, 100, 20, 0.05, 0.03, "call") is None


def test_volatilite_implicite_sur_prix_absurde():
    """Un prix sous la borne d'arbitrage n'a pas de solution."""
    assert volatilite_implicite(0.001, 100, 50, 1.0, 0.03, "call") is None


# ---------------------------------------------------------------------------
# Delta-hedging
# ---------------------------------------------------------------------------

def test_hedging_reproductible():
    """Une meme graine doit donner exactement le meme resultat."""
    a = simule_delta_hedging(100, 100, 1, 0.03, 0.20, 50, seed=7)
    b = simule_delta_hedging(100, 100, 1, 0.03, 0.20, 50, seed=7)
    assert a["pnl"] == b["pnl"]


def test_hedging_n_altere_pas_l_etat_aleatoire_global():
    """La simulation utilise un generateur local, pas le seed global NumPy."""
    np.random.seed(123)
    attendu = np.random.rand()

    np.random.seed(123)
    simule_delta_hedging(100, 100, 1, 0.03, 0.20, 50, seed=7)
    obtenu = np.random.rand()

    assert attendu == obtenu


def test_hedging_pnl_moyen_proche_de_zero():
    """La couverture neutralise le risque, elle ne genere pas de profit."""
    pnls = [
        simule_delta_hedging(100, 100, 1, 0.03, 0.20, 50, seed=i)["pnl"]
        for i in range(200)
    ]
    prime = simule_delta_hedging(100, 100, 1, 0.03, 0.20, 50, seed=0)["prime"]

    # La moyenne doit rester tres petite devant la prime encaissee.
    assert abs(np.mean(pnls)) < 0.1 * prime


def test_hedging_erreur_decroit_en_racine_de_n():
    """Multiplier la frequence par 25 doit diviser l'ecart-type par ~5."""
    def ecart_type(n):
        pnls = [
            simule_delta_hedging(100, 100, 1, 0.03, 0.20, n, seed=i)["pnl"]
            for i in range(200)
        ]
        return float(np.std(pnls))

    grossier = ecart_type(10)
    fin = ecart_type(250)
    ratio = grossier / fin

    # Theorie : sqrt(25) = 5. On laisse une marge pour le bruit
    # d'echantillonnage sur 200 trajectoires.
    assert 3.5 < ratio < 7.0


def test_hedging_position_bornee():
    """La position en delta d'un call vendu reste entre 0 et 1 action."""
    resultat = simule_delta_hedging(100, 100, 1, 0.03, 0.20, 100, seed=3)
    assert resultat["positions"].min() >= 0
    assert resultat["positions"].max() <= 1


def test_hedging_trajectoire_positive():
    """Un mouvement brownien geometrique ne peut pas devenir negatif."""
    resultat = simule_delta_hedging(100, 100, 1, 0.03, 0.20, 250, seed=11)
    assert (resultat["prix"] > 0).all()


# ---------------------------------------------------------------------------
# Robustesse
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("S,K,T,r,sigma", [
    (100, 100, 1 / 365, 0.03, 0.20),    # echeance 1 jour
    (100, 100, 1, 0.03, 0.01),          # volatilite 1%
    (100, 100, 1, 0.03, 1.50),          # volatilite 150%
    (100, 100, 1, 0.0, 0.20),           # taux nul
    (100, 100, 2, 0.10, 0.20),          # taux eleve
])
def test_pas_de_valeur_aberrante_en_regime_extreme(S, K, T, r, sigma):
    """Aucun NaN ni infini, quels que soient les parametres."""
    valeurs = [
        black_scholes(S, K, T, r, sigma, "call"),
        black_scholes(S, K, T, r, sigma, "put"),
        delta(S, K, T, r, sigma, "call"),
        gamma(S, K, T, r, sigma),
        vega(S, K, T, r, sigma),
        theta(S, K, T, r, sigma, "call"),
        rho(S, K, T, r, sigma, "call"),
        binomial_tree(S, K, T, r, sigma, "call", N=200),
        simule_delta_hedging(S, K, T, r, sigma, 20, seed=1)["pnl"],
    ]
    assert all(np.isfinite(v) for v in valeurs)


# ---------------------------------------------------------------------------
# Smile de volatilite
#
# calcule_smile ne fait aucun appel reseau : on lui fabrique des chaines
# d'options a partir d'une volatilite connue, puis on verifie qu'elle la
# retrouve. C'est precisement ce que le decouplage rend possible.
# ---------------------------------------------------------------------------

def chaine_synthetique(spot, r, T, fonction_vol, pas=5.0, largeur=0.20):
    """Fabrique des calls et puts cotes selon une volatilite imposee."""
    calls, puts = [], []
    strike = spot * (1 - largeur)

    while strike <= spot * (1 + largeur):
        sigma = fonction_vol(strike)
        calls.append({
            "strike": strike,
            "lastPrice": black_scholes(spot, strike, T, r, sigma, "call"),
        })
        puts.append({
            "strike": strike,
            "lastPrice": black_scholes(spot, strike, T, r, sigma, "put"),
        })
        strike += pas

    return calls, puts


def test_smile_retrouve_une_volatilite_constante():
    """Sur des prix generes a vol constante, le smile doit etre plat."""
    spot, r, T, sigma = 300.0, 0.03, 45 / 365, 0.25
    calls, puts = chaine_synthetique(spot, r, T, lambda k: sigma)

    strikes, vols = calcule_smile(calls, puts, spot, r, T)

    assert len(strikes) > 5
    for v in vols:
        assert v == pytest.approx(sigma, abs=1e-5)


def test_smile_retrouve_un_skew_impose():
    """Sur des prix generes avec un skew, la courbe doit le reproduire."""
    spot, r, T = 300.0, 0.03, 45 / 365

    def vol_vraie(K):
        return 0.30 - 0.20 * (K / spot - 0.90)

    calls, puts = chaine_synthetique(spot, r, T, vol_vraie)
    strikes, vols = calcule_smile(calls, puts, spot, r, T)

    assert len(strikes) > 5
    for K, v in zip(strikes, vols):
        assert v == pytest.approx(vol_vraie(K), abs=1e-5)
    # Un skew decroissant doit rester decroissant.
    assert vols[0] > vols[-1]


def test_smile_trie_par_strike_croissant():
    """Les puts et les calls sont fusionnes puis ordonnes."""
    spot, r, T = 300.0, 0.03, 45 / 365
    calls, puts = chaine_synthetique(spot, r, T, lambda k: 0.25)

    strikes, _ = calcule_smile(calls, puts, spot, r, T)

    assert strikes == sorted(strikes)
    assert len(strikes) == len(set(strikes))


def test_smile_ne_garde_que_le_hors_monnaie():
    """Puts sous le spot, calls au-dessus, dans une bande de plus ou moins 15%."""
    spot, r, T = 300.0, 0.03, 45 / 365
    calls, puts = chaine_synthetique(spot, r, T, lambda k: 0.25, largeur=0.40)

    strikes, _ = calcule_smile(calls, puts, spot, r, T)

    assert min(strikes) > spot * 0.85
    assert max(strikes) < spot * 1.15


def test_smile_ecarte_les_contrats_sans_liquidite():
    """Un prix sous 0.10 signale un contrat non echange recemment."""
    spot, r, T = 300.0, 0.03, 45 / 365
    calls, puts = chaine_synthetique(spot, r, T, lambda k: 0.25)

    parasites = [{"strike": 305.0, "lastPrice": 0.02},
                 {"strike": 310.0, "lastPrice": 0.0}]

    avant, _ = calcule_smile(calls, puts, spot, r, T)
    apres, _ = calcule_smile(calls + parasites, puts, spot, r, T)

    assert len(apres) == len(avant)


def test_smile_gere_les_entrees_vides():
    """Aucune donnee ne doit pas lever d'exception."""
    assert calcule_smile([], [], 300.0, 0.03, 45 / 365) == ([], [])


@pytest.mark.parametrize("T_invalide", [0, -1, -0.5])
def test_smile_refuse_une_echeance_passee(T_invalide):
    """Une echeance nulle ou passee n'a pas de volatilite implicite."""
    spot, r = 300.0, 0.03
    calls, puts = chaine_synthetique(spot, r, 45 / 365, lambda k: 0.25)

    assert calcule_smile(calls, puts, spot, r, T_invalide) == ([], [])


def test_smile_survit_a_des_prix_aberrants():
    """Des prix incoherents sont ignores, pas propages."""
    spot, r, T = 300.0, 0.03, 45 / 365
    calls, puts = chaine_synthetique(spot, r, T, lambda k: 0.25)

    aberrants = [
        {"strike": 305.0, "lastPrice": 1e6},    # prix absurde
        {"strike": 310.0, "lastPrice": -5.0},   # prix negatif
    ]

    strikes, vols = calcule_smile(calls + aberrants, puts, spot, r, T)

    assert len(strikes) > 5
    for v in vols:
        assert 0.01 < v < 3
        