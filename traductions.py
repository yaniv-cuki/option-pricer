"""
Traductions de l'interface.

Chaque cle correspond a un texte affiche dans app.py.
Pour ajouter une langue : dupliquer un bloc et traduire les valeurs.
"""

TRADUCTIONS = {
    # -----------------------------------------------------------------------
    # Anglais (langue par defaut)
    # -----------------------------------------------------------------------
    "en": {
        "page_title": "Options Pricer",
        "app_title": "European Options Pricer - Black-Scholes",
        "app_intro": (
            "Pricing model with Greeks computation, comparison of numerical "
            "methods and implied volatility analysis on real market data."
        ),

        # Barre laterale
        "sidebar_header": "Market parameters",
        "sidebar_subheader": "Live market data",
        "ticker_label": "Ticker",
        "load_button": "Load market data",
        "load_error": "Ticker not found or data unavailable.",
        "load_success": "Spot: {spot:.2f} | Historical vol: {vol:.2%}",
        "slider_spot": "Underlying price (S)",
        "slider_strike": "Strike (K)",
        "slider_days": "Days to expiry",
        "slider_rate": "Risk-free rate (%)",
        "slider_vol": "Volatility (%)",
        "select_type": "Option type",
        "option_call": "call",
        "option_put": "put",

        # Bandeau live
        "live_unavailable": "Intraday data unavailable for this ticker.",
        "live_meta": "Delayed data ~15 min &nbsp;|&nbsp; Updated {heure}",

        # Prix
        "header_price": "Option price",
        "metric_price": "Black-Scholes price",

        # Grecques
        "header_greeks": "Greeks",
        "greek_delta": "Delta",
        "greek_gamma": "Gamma",
        "greek_vega": "Vega",
        "greek_theta": "Theta (daily)",
        "greek_rho": "Rho",

        # Methodes
        "header_methods": "Pricing methods comparison",
        "method_bs": "Black-Scholes",
        "method_mc": "Monte Carlo",
        "method_bin_eu": "Binomial (European)",
        "method_bin_us": "Binomial (American)",
        "caption_methods": (
            "Deltas shown under each method are measured against Black-Scholes, "
            "except for the American one (measured against the European binomial, "
            "which gives the early exercise premium)."
        ),

        # Profil du delta
        "header_delta_profile": "Delta profile against the underlying",
        "axis_underlying": "Underlying price",
        "axis_delta": "Delta",
        "label_strike": "Strike {K:.0f}",
        "label_spot": "Spot {S:.0f}",
        "caption_delta": (
            "The slope of this curve is the gamma: it peaks around the strike "
            "and steepens sharply as expiry approaches."
        ),

        # Decomposition
        "header_decomposition": "Value breakdown and payoff profile",
        "metric_intrinsic": "Intrinsic value",
        "metric_time_value": "Time value",
        "metric_breakeven": "Breakeven at expiry",
        "legend_today": "Value today ({jours} days)",
        "legend_payoff": "Payoff at expiry",
        "axis_option_value": "Option value",
        "caption_decomposition": (
            "The vertical gap between the two curves is the time value. "
            "It decays as expiry approaches (an effect measured by theta)."
        ),

        # Smile
        "header_smile": "Implied volatility smile (real data)",
        "smile_intro": (
            "This section computes implied volatility from options actually "
            "quoted on the market, using out-of-the-money contracts "
            "(puts below spot, calls above)."
        ),
        "smile_button": "Analyse the volatility smile",
        "smile_no_expiry": "No expiry available for this ticker.",
        "smile_fetch_error": "Could not retrieve expiries: {erreur}",
        "smile_expiry_label": "Expiry",
        "smile_spinner": "Computing implied volatilities...",
        "smile_few_points": (
            "Not enough usable points for this expiry (illiquid options)."
        ),
        "smile_points": "Points computed",
        "smile_iv_atm": "ATM implied vol",
        "smile_hist_vol": "Historical vol",
        "axis_strike": "Strike",
        "axis_iv": "Implied volatility",
        "label_hist_vol": "Historical vol",
        "caption_smile": (
            "If Black-Scholes were exact, this curve would be flat. Its slope "
            "(skew) reflects the premium the market pays for downside protection."
        ),
    },

    # -----------------------------------------------------------------------
    # Francais
    # -----------------------------------------------------------------------
    "fr": {
        "page_title": "Pricer d'options",
        "app_title": "Pricer d'options europeennes - Black-Scholes",
        "app_intro": (
            "Modele de pricing avec calcul des grecques, comparaison de methodes "
            "numeriques et analyse de la volatilite implicite sur donnees reelles."
        ),

        # Barre laterale
        "sidebar_header": "Parametres de marche",
        "sidebar_subheader": "Donnees de marche reelles",
        "ticker_label": "Ticker",
        "load_button": "Charger les donnees du marche",
        "load_error": "Ticker introuvable ou donnees indisponibles.",
        "load_success": "Spot : {spot:.2f} | Vol historique : {vol:.2%}",
        "slider_spot": "Prix du sous-jacent (S)",
        "slider_strike": "Strike (K)",
        "slider_days": "Jours avant expiration",
        "slider_rate": "Taux sans risque (%)",
        "slider_vol": "Volatilite (%)",
        "select_type": "Type d'option",
        "option_call": "call",
        "option_put": "put",

        # Bandeau live
        "live_unavailable": "Donnees intraday indisponibles pour ce ticker.",
        "live_meta": "Donnees differees ~15 min &nbsp;|&nbsp; MAJ {heure}",

        # Prix
        "header_price": "Prix de l'option",
        "metric_price": "Prix Black-Scholes",

        # Grecques
        "header_greeks": "Grecques",
        "greek_delta": "Delta",
        "greek_gamma": "Gamma",
        "greek_vega": "Vega",
        "greek_theta": "Theta (jour)",
        "greek_rho": "Rho",

        # Methodes
        "header_methods": "Comparaison des methodes de pricing",
        "method_bs": "Black-Scholes",
        "method_mc": "Monte Carlo",
        "method_bin_eu": "Binomial (europeen)",
        "method_bin_us": "Binomial (americain)",
        "caption_methods": (
            "Les ecarts affiches sous chaque methode sont mesures par rapport a "
            "Black-Scholes, sauf pour l'americain (mesure vs binomial europeen, "
            "ce qui donne la prime d'exercice anticipe)."
        ),

        # Profil du delta
        "header_delta_profile": "Profil du Delta en fonction du sous-jacent",
        "axis_underlying": "Prix du sous-jacent",
        "axis_delta": "Delta",
        "label_strike": "Strike {K:.0f}",
        "label_spot": "Spot {S:.0f}",
        "caption_delta": (
            "La pente de cette courbe est le gamma : elle est maximale autour du "
            "strike, et se redresse brutalement a l'approche de l'echeance."
        ),

        # Decomposition
        "header_decomposition": "Decomposition de la valeur et profil de gain",
        "metric_intrinsic": "Valeur intrinseque",
        "metric_time_value": "Valeur temps",
        "metric_breakeven": "Point mort a l'echeance",
        "legend_today": "Valeur aujourd'hui ({jours} jours)",
        "legend_payoff": "Payoff a l'echeance",
        "axis_option_value": "Valeur de l'option",
        "caption_decomposition": (
            "L'ecart vertical entre les deux courbes represente la valeur temps. "
            "Elle disparait progressivement a mesure que l'echeance approche "
            "(effet mesure par le theta)."
        ),

        # Smile
        "header_smile": "Smile de volatilite implicite (donnees reelles)",
        "smile_intro": (
            "Cette section calcule la volatilite implicite a partir des prix "
            "d'options reellement cotes sur le marche, en utilisant les options "
            "hors de la monnaie (puts sous le spot, calls au-dessus)."
        ),
        "smile_button": "Analyser le smile de volatilite",
        "smile_no_expiry": "Aucune echeance disponible pour ce ticker.",
        "smile_fetch_error": "Impossible de recuperer les echeances : {erreur}",
        "smile_expiry_label": "Echeance",
        "smile_spinner": "Calcul des volatilites implicites en cours...",
        "smile_few_points": (
            "Pas assez de points exploitables pour cette echeance "
            "(options peu liquides)."
        ),
        "smile_points": "Points calcules",
        "smile_iv_atm": "Vol implicite ATM",
        "smile_hist_vol": "Vol historique",
        "axis_strike": "Strike",
        "axis_iv": "Volatilite implicite",
        "label_hist_vol": "Vol historique",
        "caption_smile": (
            "Si Black-Scholes etait exact, cette courbe serait horizontale. "
            "Sa pente (skew) traduit la prime payee par le marche pour se "
            "proteger contre une baisse."
        ),
    },
}

# Noms affiches dans le selecteur de langue
LANGUES = {
    "en": "English",
    "fr": "Francais",
}