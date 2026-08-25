import streamlit as st
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt


from pricer import black_scholes, delta, gamma, vega, theta, rho, monte_carlo_pricer, binomial_tree

st.set_page_config(page_title="Pricer d'options", layout="wide")

st.title("Pricer d'options europeennes - Black-Scholes")
st.write("Modele de pricing avec calcul des grecques et comparaison de methodes numeriques.")

st.sidebar.header("Parametres de marche")
st.sidebar.subheader("Donnees de marche reelles")

ticker_input = st.sidebar.text_input("Ticker", value="AAPL")

@st.cache_data(ttl=300)
def charger_donnees_marche(symbole):
    tk = yf.Ticker(symbole)
    historique = tk.history(period="1y")

    if historique.empty:
        return None, None

    spot = historique["Close"].iloc[-1]
    rendements_log = np.log(historique["Close"] / historique["Close"].shift(1))
    vol = rendements_log.std() * np.sqrt(252)

    return spot, vol

if st.sidebar.button("Charger les donnees du marche"):
    spot_charge, vol_chargee = charger_donnees_marche(ticker_input)

    if spot_charge is None:
        st.sidebar.error("Ticker introuvable ou donnees indisponibles.")
    else:
        st.session_state["spot_charge"] = float(spot_charge)
        st.session_state["vol_chargee"] = float(vol_chargee)
        st.session_state["strike_defaut"] = float(round(spot_charge))
        st.sidebar.success(f"Spot : {spot_charge:.2f} | Vol historique : {vol_chargee:.2%}")

spot_defaut = st.session_state.get("spot_charge", 310.0)
vol_defaut = st.session_state.get("vol_chargee", 0.25) * 100
strike_defaut = st.session_state.get("strike_defaut", 310.0)

S = st.sidebar.slider("Prix du sous-jacent (S)", 50.0, 500.0, spot_defaut, step=1.0)
K = st.sidebar.slider("Strike (K)", 50.0, 500.0, strike_defaut, step=1.0)
T_jours = st.sidebar.slider("Jours avant expiration", 1, 730, 30)
r_pct = st.sidebar.slider("Taux sans risque (%)", 0.0, 10.0, 3.0, step=0.1)
sigma_pct = st.sidebar.slider("Volatilite (%)", 1.0, 100.0, vol_defaut, step=0.5)
option_type = st.sidebar.selectbox("Type d'option", ["call", "put"])

T = T_jours / 365
r = r_pct / 100
sigma = sigma_pct / 100

prix = black_scholes(S, K, T, r, sigma, option_type)

st.header("Prix de l'option")
st.metric(label="Prix Black-Scholes", value=f"{prix:.4f}")

st.header("Grecques")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Delta", f"{delta(S, K, T, r, sigma, option_type):.4f}")
col2.metric("Gamma", f"{gamma(S, K, T, r, sigma):.4f}")
col3.metric("Vega", f"{vega(S, K, T, r, sigma):.4f}")
col4.metric("Theta (jour)", f"{theta(S, K, T, r, sigma, option_type):.4f}")
col5.metric("Rho", f"{rho(S, K, T, r, sigma, option_type):.4f}")

st.header("Comparaison des methodes de pricing")

prix_mc = monte_carlo_pricer(S, K, T, r, sigma, option_type)
prix_bin_eu = binomial_tree(S, K, T, r, sigma, option_type, exercise_type="europeenne", N=500)
prix_bin_us = binomial_tree(S, K, T, r, sigma, option_type, exercise_type="americaine", N=500)

col_a, col_b, col_c, col_d = st.columns(4)

col_a.metric("Black-Scholes", f"{prix:.4f}")
col_b.metric("Monte Carlo", f"{prix_mc:.4f}", delta=f"{prix_mc - prix:.4f}")
col_c.metric("Binomial (europeen)", f"{prix_bin_eu:.4f}", delta=f"{prix_bin_eu - prix:.4f}")
col_d.metric("Binomial (americain)", f"{prix_bin_us:.4f}", delta=f"{prix_bin_us - prix_bin_eu:.4f}")

st.caption("Les ecarts affiches sous chaque methode sont mesures par rapport a Black-Scholes, sauf pour l'americain (mesure vs binomial europeen, ce qui donne la prime d'exercice anticipe).")
st.header("Profil du Delta en fonction du sous-jacent")

spots_graphique = np.linspace(S * 0.6, S * 1.4, 150)
deltas_graphique = [delta(s, K, T, r, sigma, option_type) for s in spots_graphique]

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(spots_graphique, deltas_graphique, linewidth=2)
ax.axvline(K, color="red", linestyle="--", label=f"Strike = {K:.0f}")
ax.axvline(S, color="green", linestyle=":", label=f"Spot actuel = {S:.0f}")
ax.set_xlabel("Prix du sous-jacent")
ax.set_ylabel("Delta")
ax.grid(True, alpha=0.3)
ax.legend()

st.pyplot(fig)

