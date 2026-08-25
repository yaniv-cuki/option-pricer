"""
Dashboard Streamlit - Pricer d'options europeennes.

Interface interactive pour le moteur de pricing defini dans pricer.py.
Lancer avec :  streamlit run app.py
"""

import streamlit as st
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

from pricer import (
    black_scholes,
    delta,
    gamma,
    vega,
    theta,
    rho,
    monte_carlo_pricer,
    binomial_tree,
    volatilite_implicite,
    calcule_smile,
)


# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Pricer d'options", layout="wide")

st.title("Pricer d'options europeennes - Black-Scholes")
st.write(
    "Modele de pricing avec calcul des grecques, comparaison de methodes "
    "numeriques et analyse de la volatilite implicite sur donnees reelles."
)


# ---------------------------------------------------------------------------
# Fonctions de recuperation des donnees de marche (mises en cache)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def charger_donnees_marche(symbole):
    """Recupere le spot et la volatilite historique annualisee sur 1 an."""
    tk = yf.Ticker(symbole)
    historique = tk.history(period="1y")

    if historique.empty:
        return None, None

    spot = historique["Close"].iloc[-1]
    rendements_log = np.log(historique["Close"] / historique["Close"].shift(1))
    vol = rendements_log.std() * np.sqrt(252)

    return spot, vol


@st.cache_data(ttl=300)
def charger_echeances(symbole):
    """Recupere la liste des dates d'expiration d'options disponibles."""
    tk = yf.Ticker(symbole)
    return list(tk.options)


# ---------------------------------------------------------------------------
# Barre laterale : donnees reelles + parametres du modele
# ---------------------------------------------------------------------------

st.sidebar.header("Parametres de marche")
st.sidebar.subheader("Donnees de marche reelles")

ticker_input = st.sidebar.text_input("Ticker", value="AAPL")

if st.sidebar.button("Charger les donnees du marche"):
    spot_charge, vol_chargee = charger_donnees_marche(ticker_input)

    if spot_charge is None:
        st.sidebar.error("Ticker introuvable ou donnees indisponibles.")
    else:
        st.session_state["spot_charge"] = float(spot_charge)
        st.session_state["vol_chargee"] = float(vol_chargee)
        st.session_state["strike_defaut"] = float(round(spot_charge))
        st.sidebar.success(
            f"Spot : {spot_charge:.2f} | Vol historique : {vol_chargee:.2%}"
        )

# Valeurs par defaut des curseurs, bornees pour rester dans la plage autorisee
spot_defaut = float(np.clip(st.session_state.get("spot_charge", 310.0), 50.0, 500.0))
strike_defaut = float(np.clip(st.session_state.get("strike_defaut", 310.0), 50.0, 500.0))
vol_defaut = float(np.clip(st.session_state.get("vol_chargee", 0.25) * 100, 1.0, 100.0))

S = st.sidebar.slider("Prix du sous-jacent (S)", 50.0, 500.0, spot_defaut, step=1.0)
K = st.sidebar.slider("Strike (K)", 50.0, 500.0, strike_defaut, step=1.0)
T_jours = st.sidebar.slider("Jours avant expiration", 1, 730, 30)
r_pct = st.sidebar.slider("Taux sans risque (%)", 0.0, 10.0, 3.0, step=0.1)
sigma_pct = st.sidebar.slider("Volatilite (%)", 1.0, 100.0, vol_defaut, step=0.5)
option_type = st.sidebar.selectbox("Type d'option", ["call", "put"])

T = T_jours / 365
r = r_pct / 100
sigma = sigma_pct / 100


# ---------------------------------------------------------------------------
# Prix de l'option
# ---------------------------------------------------------------------------

prix = black_scholes(S, K, T, r, sigma, option_type)

st.header("Prix de l'option")
st.metric(label="Prix Black-Scholes", value=f"{prix:.4f}")


# ---------------------------------------------------------------------------
# Grecques
# ---------------------------------------------------------------------------

st.header("Grecques")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Delta", f"{delta(S, K, T, r, sigma, option_type):.4f}")
col2.metric("Gamma", f"{gamma(S, K, T, r, sigma):.4f}")
col3.metric("Vega", f"{vega(S, K, T, r, sigma):.4f}")
col4.metric("Theta (jour)", f"{theta(S, K, T, r, sigma, option_type):.4f}")
col5.metric("Rho", f"{rho(S, K, T, r, sigma, option_type):.4f}")


# ---------------------------------------------------------------------------
# Comparaison des trois methodes de pricing
# ---------------------------------------------------------------------------

st.header("Comparaison des methodes de pricing")

prix_mc = monte_carlo_pricer(S, K, T, r, sigma, option_type)
prix_bin_eu = binomial_tree(S, K, T, r, sigma, option_type,
                            exercise_type="europeenne", N=500)
prix_bin_us = binomial_tree(S, K, T, r, sigma, option_type,
                            exercise_type="americaine", N=500)

col_a, col_b, col_c, col_d = st.columns(4)

col_a.metric("Black-Scholes", f"{prix:.4f}")
col_b.metric("Monte Carlo", f"{prix_mc:.4f}", delta=f"{prix_mc - prix:.4f}")
col_c.metric("Binomial (europeen)", f"{prix_bin_eu:.4f}",
             delta=f"{prix_bin_eu - prix:.4f}")
col_d.metric("Binomial (americain)", f"{prix_bin_us:.4f}",
             delta=f"{prix_bin_us - prix_bin_eu:.4f}")

st.caption(
    "Les ecarts affiches sous chaque methode sont mesures par rapport a "
    "Black-Scholes, sauf pour l'americain (mesure vs binomial europeen, "
    "ce qui donne la prime d'exercice anticipe)."
)


# ---------------------------------------------------------------------------
# Profil du Delta en fonction du sous-jacent
# ---------------------------------------------------------------------------

st.header("Profil du Delta en fonction du sous-jacent")

spots_graphique = np.linspace(S * 0.6, S * 1.4, 150)
deltas_graphique = [delta(s, K, T, r, sigma, option_type) for s in spots_graphique]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=spots_graphique,
    y=deltas_graphique,
    mode="lines",
    name="Delta",
    line=dict(width=3, color="#4C9BE8"),
))

fig.add_vline(x=K, line_dash="dash", line_color="#E8574C",
              annotation_text=f"Strike {K:.0f}", annotation_position="top")
fig.add_vline(x=S, line_dash="dot", line_color="#4CE874",
              annotation_text=f"Spot {S:.0f}", annotation_position="bottom")

fig.update_layout(
    template="plotly_dark",
    xaxis_title="Prix du sous-jacent",
    yaxis_title="Delta",
    height=400,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=40, t=30, b=40),
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "La pente de cette courbe est le gamma : elle est maximale autour du strike, "
    "et se redresse brutalement a l'approche de l'echeance."
)


# ---------------------------------------------------------------------------
# Decomposition de la valeur et profil de gain
# ---------------------------------------------------------------------------

st.header("Decomposition de la valeur et profil de gain")

if option_type == "call":
    intrinseque_actuelle = max(S - K, 0)
    point_mort = K + prix
else:
    intrinseque_actuelle = max(K - S, 0)
    point_mort = K - prix

valeur_temps = prix - intrinseque_actuelle

col_i, col_j, col_k = st.columns(3)
col_i.metric("Valeur intrinseque", f"{intrinseque_actuelle:.2f}")
col_j.metric("Valeur temps", f"{valeur_temps:.2f}")
col_k.metric("Point mort a l'echeance", f"{point_mort:.2f}")

spots_payoff = np.linspace(S * 0.6, S * 1.4, 200)

if option_type == "call":
    payoff_echeance = np.maximum(spots_payoff - K, 0)
else:
    payoff_echeance = np.maximum(K - spots_payoff, 0)

valeur_aujourdhui = [black_scholes(s, K, T, r, sigma, option_type)
                     for s in spots_payoff]

fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=spots_payoff,
    y=valeur_aujourdhui,
    mode="lines",
    name=f"Valeur aujourd'hui ({T_jours} jours)",
    line=dict(width=3, color="#4C9BE8"),
))

fig3.add_trace(go.Scatter(
    x=spots_payoff,
    y=payoff_echeance,
    mode="lines",
    name="Payoff a l'echeance",
    line=dict(width=2, color="#E8A44C", dash="dash"),
))

fig3.add_vline(x=K, line_dash="dot", line_color="#888888",
               annotation_text=f"Strike {K:.0f}", annotation_position="top left")

fig3.update_layout(
    template="plotly_dark",
    xaxis_title="Prix du sous-jacent",
    yaxis_title="Valeur de l'option",
    height=450,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=40, t=30, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig3, use_container_width=True)

st.caption(
    "L'ecart vertical entre les deux courbes represente la valeur temps. "
    "Elle disparait progressivement a mesure que l'echeance approche "
    "(effet mesure par le theta)."
)


# ---------------------------------------------------------------------------
# Smile de volatilite implicite sur donnees reelles
# ---------------------------------------------------------------------------

st.header("Smile de volatilite implicite (donnees reelles)")

st.write(
    "Cette section calcule la volatilite implicite a partir des prix d'options "
    "reellement cotes sur le marche, en utilisant les options hors de la monnaie "
    "(puts sous le spot, calls au-dessus)."
)

if st.button("Analyser le smile de volatilite"):
    try:
        echeances = charger_echeances(ticker_input)

        if len(echeances) == 0:
            st.error("Aucune echeance disponible pour ce ticker.")
        else:
            st.session_state["echeances"] = echeances
    except Exception as e:
        st.error(f"Impossible de recuperer les echeances : {e}")

if "echeances" in st.session_state:
    echeances = st.session_state["echeances"]
    index_defaut = min(7, len(echeances) - 1)
    echeance_choisie = st.selectbox("Echeance", echeances, index=index_defaut)

    with st.spinner("Calcul des volatilites implicites en cours..."):
        ticker_obj = yf.Ticker(ticker_input)
        strikes_smile, vols_smile, T_smile = calcule_smile(
            ticker_obj, echeance_choisie, S, r
        )

    if len(strikes_smile) < 3:
        st.warning(
            "Pas assez de points exploitables pour cette echeance "
            "(options peu liquides)."
        )
    else:
        col_x, col_y, col_z = st.columns(3)
        col_x.metric("Points calcules", len(strikes_smile))
        col_y.metric("Vol implicite ATM",
                     f"{np.interp(S, strikes_smile, vols_smile):.2%}")
        col_z.metric("Vol historique", f"{sigma:.2%}")

        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=strikes_smile,
            y=vols_smile,
            mode="lines+markers",
            name="Volatilite implicite",
            line=dict(width=3, color="#4C9BE8"),
            marker=dict(size=8),
        ))

        fig2.add_vline(x=S, line_dash="dash", line_color="#E8574C",
                       annotation_text=f"Spot {S:.0f}", annotation_position="top")
        fig2.add_hline(y=sigma, line_dash="dot", line_color="#E8A44C",
                       annotation_text=f"Vol historique {sigma:.1%}",
                       annotation_position="top left")

        fig2.update_layout(
            template="plotly_dark",
            xaxis_title="Strike",
            yaxis_title="Volatilite implicite",
            yaxis_tickformat=".1%",
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=30, b=40),
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.caption(
            "Si Black-Scholes etait exact, cette courbe serait horizontale. "
            "Sa pente (skew) traduit la prime payee par le marche pour se "
            "proteger contre une baisse."
        )
        