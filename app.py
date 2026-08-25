import streamlit as st
import numpy as np
import yfinance as yf

from pricer import black_scholes, delta, gamma, vega, theta, rho, monte_carlo_pricer, binomial_tree

st.set_page_config(page_title="Pricer d'options", layout="wide")

st.title("Pricer d'options europeennes - Black-Scholes")
st.write("Modele de pricing avec calcul des grecques et comparaison de methodes numeriques.")

st.sidebar.header("Parametres de marche")

S = st.sidebar.slider("Prix du sous-jacent (S)", 50.0, 500.0, 310.0, step=1.0)
K = st.sidebar.slider("Strike (K)", 50.0, 500.0, 310.0, step=1.0)
T_jours = st.sidebar.slider("Jours avant expiration", 1, 730, 30)
r_pct = st.sidebar.slider("Taux sans risque (%)", 0.0, 10.0, 3.0, step=0.1)
sigma_pct = st.sidebar.slider("Volatilite (%)", 1.0, 100.0, 25.0, step=0.5)
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

