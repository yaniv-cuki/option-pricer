"""
Dashboard Streamlit - Pricer d'options europeennes.

Interface interactive pour le moteur de pricing defini dans pricer.py.
Textes de l'interface stockes dans traductions.py.
Lancer avec :  streamlit run app.py
"""

from datetime import datetime

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


from pricer import (
    binomial_tree,
    black_scholes,
    calcule_smile,
    delta,
    gamma,
    monte_carlo_pricer,
    rho,
    theta,
    vega,
    simule_delta_hedging,
    
)
from traductions import LANGUES, TRADUCTIONS
from plotly.subplots import make_subplots



# ---------------------------------------------------------------------------
# Langue de l'interface
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Options Pricer", layout="wide")

langue = st.sidebar.selectbox(
    "Language / Langue",
    options=list(LANGUES.keys()),
    format_func=lambda code: LANGUES[code],
)


def t(cle, **valeurs):
    """Renvoie le texte associe a une cle, dans la langue active.

    Les valeurs nommees eventuelles sont injectees dans le texte
    (par exemple t("label_strike", K=310) -> "Strike 310").
    """
    texte = TRADUCTIONS[langue][cle]
    return texte.format(**valeurs) if valeurs else texte


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
/* --- Fond d'ambiance --- */
.stApp {
    background:
        radial-gradient(1200px 600px at 15% -10%, rgba(76,155,232,0.18), transparent 60%),
        radial-gradient(1000px 500px at 85% 0%, rgba(245,165,36,0.10), transparent 55%),
        linear-gradient(180deg, #0B1020 0%, #0E1428 100%);
}

/* --- Cartes de metriques en verre --- */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    transition: transform .25s ease, border-color .25s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    border-color: rgba(245,165,36,0.45);
}

[data-testid="stMetricValue"] {
    font-family: "SF Mono", "JetBrains Mono", Menlo, monospace;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.5px;
}

[data-testid="stMetricLabel"] {
    text-transform: uppercase;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    opacity: 0.65;
}

/* --- Barre laterale --- */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.08);
}

h1, h2, h3 { letter-spacing: -0.02em; }

/* --- Bandeau live --- */
.live-bar {
    display: flex; align-items: center; gap: 26px; flex-wrap: wrap;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 14px 22px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}

.live-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #22C55E; display: inline-block; margin-right: 10px;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(34,197,94,0.6); }
    70%  { box-shadow: 0 0 0 10px rgba(34,197,94,0); }
    100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
}

.live-ticker { font-size: 1.45rem; font-weight: 700; letter-spacing: 0.04em; }

.live-price, .live-change {
    font-family: "SF Mono","JetBrains Mono",Menlo,monospace;
    font-variant-numeric: tabular-nums;
}

.live-price { font-size: 1.75rem; font-weight: 600; }
.live-change { font-size: 1rem; padding: 4px 10px; border-radius: 8px; }
.up   { color: #22C55E; background: rgba(34,197,94,0.12); }
.down { color: #EF4444; background: rgba(239,68,68,0.12); }

.live-meta {
    margin-left: auto; font-size: 0.72rem; opacity: 0.55;
    letter-spacing: 0.06em; text-transform: uppercase;
}

/* --- Pied de page --- */
.footer {
    margin-top: 60px; padding: 22px 0 10px 0;
    border-top: 1px solid rgba(255,255,255,0.08);
    font-size: 0.82rem; opacity: 0.6; text-align: center;
}

.footer a { color: #F5A524; text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* --- Accessibilite : respect des preferences systeme --- */
@media (prefers-reduced-motion: reduce) {
    [data-testid="stMetric"] { transition: none; }
    .live-dot { animation: none; }
}
</style>
""",
    unsafe_allow_html=True,
)

st.title(t("app_title"))
st.write(t("app_intro"))


# ---------------------------------------------------------------------------
# Recuperation des donnees de marche (mise en cache)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def charger_donnees_marche(symbole):
    """Recupere le spot courant et la volatilite historique annualisee sur 1 an.

    Le spot est pris sur la serie intraday quand elle est disponible, pour
    rester coherent avec le prix affiche dans le bandeau de cotation.
    """
    tk = yf.Ticker(symbole)
    historique = tk.history(period="1y")

    if historique.empty:
        return None, None

    rendements_log = np.log(historique["Close"] / historique["Close"].shift(1))
    vol = rendements_log.std() * np.sqrt(252)

    donnees_intraday = charger_intraday(symbole)

    if donnees_intraday is not None:
        spot = donnees_intraday["dernier"]
    else:
        spot = float(historique["Close"].iloc[-1])

    return spot, vol


@st.cache_data(ttl=300)
def charger_echeances(symbole):
    """Recupere la liste des dates d'expiration d'options disponibles."""
    tk = yf.Ticker(symbole)
    return list(tk.options)


@st.cache_data(ttl=60)
def charger_intraday(symbole):
    """Recupere la serie intraday et la variation depuis la cloture precedente."""
    tk = yf.Ticker(symbole)
    intraday = tk.history(period="1d", interval="5m")
    recent = tk.history(period="5d")

    if intraday.empty or len(recent) < 2:
        return None

    dernier = float(intraday["Close"].iloc[-1])
    cloture_precedente = float(recent["Close"].iloc[-2])
    variation = dernier - cloture_precedente

    return {
        "dernier": dernier,
        "variation": variation,
        "variation_pct": variation / cloture_precedente * 100,
        "serie": [float(x) for x in intraday["Close"].tolist()],
    }


@st.fragment(run_every="30s")
def bandeau_live(symbole):
    """Bandeau de cotation auto-rafraichi toutes les 30 secondes."""
    donnees = charger_intraday(symbole)

    if donnees is None:
        st.warning(t("live_unavailable"))
        return

    hausse = donnees["variation"] >= 0
    sens = "up" if hausse else "down"
    signe = "+" if hausse else ""
    meta = t("live_meta", heure=datetime.now().strftime("%H:%M:%S"))

    st.markdown(
        f"""
    <div class="live-bar">
        <span>
            <span class="live-dot"></span>
            <span class="live-ticker">{symbole.upper()}</span>
        </span>
        <span class="live-price">{donnees['dernier']:.2f}</span>
        <span class="live-change {sens}">
            {signe}{donnees['variation']:.2f} ({signe}{donnees['variation_pct']:.2f}%)
        </span>
        <span class="live-meta">{meta}</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    couleur = "#22C55E" if hausse else "#EF4444"
    remplissage = "rgba(34,197,94,0.12)" if hausse else "rgba(239,68,68,0.12)"

    fig_spark = go.Figure()
    fig_spark.add_trace(go.Scatter(
        y=donnees["serie"],
        mode="lines",
        line=dict(width=2, color=couleur),
        fill="tozeroy",
        fillcolor=remplissage,
        hoverinfo="skip",
    ))
    fig_spark.update_layout(
        height=90,
        margin=dict(l=0, r=0, t=4, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(
            visible=False,
            range=[min(donnees["serie"]) * 0.998, max(donnees["serie"]) * 1.002],
        ),
        showlegend=False,
    )

    st.plotly_chart(fig_spark, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Barre laterale : donnees reelles et parametres du modele
# ---------------------------------------------------------------------------

st.sidebar.header(t("sidebar_header"))
st.sidebar.subheader(t("sidebar_subheader"))

# Valeurs initiales, posees une seule fois au premier chargement.
# Les widgets sont ensuite pilotes par leur cle, ce qui les rend
# insensibles au changement de langue.
VALEURS_INITIALES = {
    "ticker": "AAPL",
    "S": 310.0,
    "K": 310.0,
    "T_jours": 30,
    "r_pct": 3.0,
    "sigma_pct": 25.0,
    "option_type": "call",
}

for cle, valeur in VALEURS_INITIALES.items():
    if cle not in st.session_state:
        st.session_state[cle] = valeur
# Au tout premier chargement, on aligne les curseurs sur le marche reel
# plutot que de laisser les valeurs de repli.
if "initialise" not in st.session_state:
    spot_init, vol_init = charger_donnees_marche(st.session_state["ticker"])

    if spot_init is not None:
        st.session_state["S"] = float(np.clip(spot_init, 50.0, 500.0))
        st.session_state["K"] = float(np.clip(round(spot_init), 50.0, 500.0))
        st.session_state["sigma_pct"] = float(np.clip(vol_init * 100, 1.0, 100.0))

    st.session_state["initialise"] = True

ticker_input = st.sidebar.text_input(t("ticker_label"), key="ticker")

if st.sidebar.button(t("load_button")):
    spot_charge, vol_chargee = charger_donnees_marche(ticker_input)

    if spot_charge is None:
        st.sidebar.error(t("load_error"))
    else:
        st.session_state["S"] = float(np.clip(spot_charge, 50.0, 500.0))
        st.session_state["K"] = float(np.clip(round(spot_charge), 50.0, 500.0))
        st.session_state["sigma_pct"] = float(np.clip(vol_chargee * 100, 1.0, 100.0))
        st.sidebar.success(t("load_success", spot=spot_charge, vol=vol_chargee))

S = st.sidebar.slider(t("slider_spot"), 50.0, 500.0, step=1.0, key="S")
K = st.sidebar.slider(t("slider_strike"), 50.0, 500.0, step=1.0, key="K")
T_jours = st.sidebar.slider(t("slider_days"), 1, 730, key="T_jours")
r_pct = st.sidebar.slider(t("slider_rate"), 0.0, 10.0, step=0.1, key="r_pct")
sigma_pct = st.sidebar.slider(t("slider_vol"), 1.0, 100.0, step=0.5, key="sigma_pct")

option_type = st.sidebar.selectbox(
    t("select_type"),
    options=["call", "put"],
    format_func=lambda code: t(f"option_{code}"),
    key="option_type",
)

T = T_jours / 365
r = r_pct / 100
sigma = sigma_pct / 100


# ---------------------------------------------------------------------------
# Bandeau de cotation
# ---------------------------------------------------------------------------

bandeau_live(ticker_input)


# ---------------------------------------------------------------------------
# Prix de l'option
# ---------------------------------------------------------------------------

prix = black_scholes(S, K, T, r, sigma, option_type)

st.header(t("header_price"))
st.metric(label=t("metric_price"), value=f"{prix:.4f}")


# ---------------------------------------------------------------------------
# Grecques
# ---------------------------------------------------------------------------

st.header(t("header_greeks"))

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(t("greek_delta"), f"{delta(S, K, T, r, sigma, option_type):.4f}")
col2.metric(t("greek_gamma"), f"{gamma(S, K, T, r, sigma):.4f}")
col3.metric(t("greek_vega"), f"{vega(S, K, T, r, sigma):.4f}")
col4.metric(t("greek_theta"), f"{theta(S, K, T, r, sigma, option_type):.4f}")
col5.metric(t("greek_rho"), f"{rho(S, K, T, r, sigma, option_type):.4f}")


# ---------------------------------------------------------------------------
# Comparaison des trois methodes de pricing
# ---------------------------------------------------------------------------

st.header(t("header_methods"))

prix_mc = monte_carlo_pricer(S, K, T, r, sigma, option_type)
prix_bin_eu = binomial_tree(S, K, T, r, sigma, option_type,
                            exercise_type="europeenne", N=500)
prix_bin_us = binomial_tree(S, K, T, r, sigma, option_type,
                            exercise_type="americaine", N=500)

col_a, col_b, col_c, col_d = st.columns(4)

col_a.metric(t("method_bs"), f"{prix:.4f}")
col_b.metric(t("method_mc"), f"{prix_mc:.4f}", delta=f"{prix_mc - prix:.4f}")
col_c.metric(t("method_bin_eu"), f"{prix_bin_eu:.4f}",
             delta=f"{prix_bin_eu - prix:.4f}")
col_d.metric(t("method_bin_us"), f"{prix_bin_us:.4f}",
             delta=f"{prix_bin_us - prix_bin_eu:.4f}")

st.caption(t("caption_methods"))


# ---------------------------------------------------------------------------
# Profil du Delta en fonction du sous-jacent
# ---------------------------------------------------------------------------

st.header(t("header_delta_profile"))

spots_graphique = np.linspace(S * 0.6, S * 1.4, 150)
deltas_graphique = [delta(s, K, T, r, sigma, option_type) for s in spots_graphique]

fig_delta = go.Figure()

fig_delta.add_trace(go.Scatter(
    x=spots_graphique,
    y=deltas_graphique,
    mode="lines",
    name=t("axis_delta"),
    line=dict(width=3, color="#4C9BE8"),
))

fig_delta.add_vline(x=K, line_dash="dash", line_color="#E8574C",
                    annotation_text=t("label_strike", K=K),
                    annotation_position="top")
fig_delta.add_vline(x=S, line_dash="dot", line_color="#4CE874",
                    annotation_text=t("label_spot", S=S),
                    annotation_position="bottom")

fig_delta.update_layout(
    template="plotly_dark",
    xaxis_title=t("axis_underlying"),
    yaxis_title=t("axis_delta"),
    height=400,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=40, t=30, b=40),
)

st.plotly_chart(fig_delta, width="stretch")

st.caption(t("caption_delta"))


# ---------------------------------------------------------------------------
# Decomposition de la valeur et profil de gain
# ---------------------------------------------------------------------------

st.header(t("header_decomposition"))

if option_type == "call":
    intrinseque_actuelle = max(S - K, 0)
    point_mort = K + prix
else:
    intrinseque_actuelle = max(K - S, 0)
    point_mort = K - prix

valeur_temps = prix - intrinseque_actuelle

col_i, col_j, col_k = st.columns(3)
col_i.metric(t("metric_intrinsic"), f"{intrinseque_actuelle:.2f}")
col_j.metric(t("metric_time_value"), f"{valeur_temps:.2f}")
col_k.metric(t("metric_breakeven"), f"{point_mort:.2f}")

spots_payoff = np.linspace(S * 0.6, S * 1.4, 200)

if option_type == "call":
    payoff_echeance = np.maximum(spots_payoff - K, 0)
else:
    payoff_echeance = np.maximum(K - spots_payoff, 0)

valeur_aujourdhui = [black_scholes(s, K, T, r, sigma, option_type)
                     for s in spots_payoff]

fig_payoff = go.Figure()

fig_payoff.add_trace(go.Scatter(
    x=spots_payoff,
    y=valeur_aujourdhui,
    mode="lines",
    name=t("legend_today", jours=T_jours),
    line=dict(width=3, color="#4C9BE8"),
))

fig_payoff.add_trace(go.Scatter(
    x=spots_payoff,
    y=payoff_echeance,
    mode="lines",
    name=t("legend_payoff"),
    line=dict(width=2, color="#E8A44C", dash="dash"),
))

fig_payoff.add_vline(x=K, line_dash="dot", line_color="#888888",
                     annotation_text=t("label_strike", K=K),
                     annotation_position="top left")

fig_payoff.update_layout(
    template="plotly_dark",
    xaxis_title=t("axis_underlying"),
    yaxis_title=t("axis_option_value"),
    height=450,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=40, t=30, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig_payoff, width="stretch")

st.caption(t("caption_decomposition"))


# ---------------------------------------------------------------------------
# Smile de volatilite implicite sur donnees reelles
# ---------------------------------------------------------------------------

st.header(t("header_smile"))
st.write(t("smile_intro"))

if st.button(t("smile_button")):
    try:
        echeances = charger_echeances(ticker_input)

        if len(echeances) == 0:
            st.error(t("smile_no_expiry"))
        else:
            st.session_state["echeances"] = echeances
    except Exception as e:
        st.error(t("smile_fetch_error", erreur=e))

if "echeances" in st.session_state:
    echeances = st.session_state["echeances"]
    index_defaut = min(7, len(echeances) - 1)
    echeance_choisie = st.selectbox(
        t("smile_expiry_label"), echeances, index=index_defaut
    )

    with st.spinner(t("smile_spinner")):
        ticker_obj = yf.Ticker(ticker_input)
        strikes_smile, vols_smile, T_smile = calcule_smile(
            ticker_obj, echeance_choisie, S, r
        )

    if len(strikes_smile) < 3:
        st.warning(t("smile_few_points"))
    else:
        col_x, col_y, col_z = st.columns(3)
        col_x.metric(t("smile_points"), len(strikes_smile))
        col_y.metric(t("smile_iv_atm"),
                     f"{np.interp(S, strikes_smile, vols_smile):.2%}")
        col_z.metric(t("smile_hist_vol"), f"{sigma:.2%}")

        fig_smile = go.Figure()

        fig_smile.add_trace(go.Scatter(
            x=strikes_smile,
            y=vols_smile,
            mode="lines+markers",
            name=t("axis_iv"),
            line=dict(width=3, color="#4C9BE8"),
            marker=dict(size=8),
        ))

        fig_smile.add_vline(x=S, line_dash="dash", line_color="#E8574C",
                            annotation_text=t("label_spot", S=S),
                            annotation_position="top")
        fig_smile.add_hline(y=sigma, line_dash="dot", line_color="#E8A44C",
                            annotation_text=t("label_hist_vol"),
                            annotation_position="bottom right")

        fig_smile.update_layout(
            template="plotly_dark",
            xaxis_title=t("axis_strike"),
            yaxis_title=t("axis_iv"),
            yaxis_tickformat=".1%",
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=30, b=40),
        )

        st.plotly_chart(fig_smile, width="stretch")

        st.caption(t("caption_smile"))

# ---------------------------------------------------------------------------
# Simulation de delta-hedging
# ---------------------------------------------------------------------------

st.header(t("header_hedging"))
st.write(t("hedging_intro"))

n_rebal = st.select_slider(
    t("hedging_freq"),
    options=[10, 25, 50, 100, 250],
    value=50,
    key="n_rebal",
)


@st.cache_data(show_spinner=False)
def calcule_convergence(S, K, T, r, sigma, frequences, n_trajectoires=150):
    """Ecart-type du P&L de couverture pour plusieurs frequences."""
    ecarts = []

    for n in frequences:
        pnls = [
            simule_delta_hedging(S, K, T, r, sigma, n, seed=i)["pnl"]
            for i in range(n_trajectoires)
        ]
        ecarts.append(float(np.std(pnls)))

    return ecarts


if st.button(t("hedging_button")):
    st.session_state["hedging_lance"] = True

if st.session_state.get("hedging_lance"):
    with st.spinner(t("hedging_spinner")):
        resultat = simule_delta_hedging(S, K, T, r, sigma, n_rebal, seed=7)
        frequences = [10, 25, 50, 100, 250]
        ecarts = calcule_convergence(S, K, T, r, sigma, tuple(frequences))

    erreur_pct = abs(resultat["pnl"]) / resultat["prime"] * 100

    col_p, col_q, col_r = st.columns(3)
    col_p.metric(t("metric_premium"), f"{resultat['prime']:.2f}")
    col_q.metric(t("metric_pnl"), f"{resultat['pnl']:+.2f}")
    col_r.metric(t("metric_hedge_error"), f"{erreur_pct:.1f}%")

    # --- Graphique 1 : trajectoire et couverture ---
    temps = np.linspace(0, 1, len(resultat["prix"]))

    fig_traj = make_subplots(specs=[[{"secondary_y": True}]])

    fig_traj.add_trace(
        go.Scatter(x=temps, y=resultat["prix"], mode="lines",
                   name=t("legend_price"),
                   line=dict(width=3, color="#4C9BE8")),
        secondary_y=False,
    )

    fig_traj.add_trace(
        go.Scatter(x=temps, y=resultat["positions"], mode="lines",
                   name=t("legend_delta_pos"),
                   line=dict(width=2, color="#F5A524")),
        secondary_y=True,
    )

    fig_traj.add_hline(y=K, line_dash="dot", line_color="#888888",
                       annotation_text=t("label_strike", K=K),
                       annotation_position="top left")

    fig_traj.update_yaxes(title_text=t("axis_price"), secondary_y=False)
    fig_traj.update_yaxes(title_text=t("axis_delta_pos"), secondary_y=True,
                          range=[0, 1])

    fig_traj.update_layout(
        template="plotly_dark",
        xaxis_title=t("axis_time"),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    )

    st.plotly_chart(fig_traj, width="stretch")
    st.caption(t("caption_trajectory"))

    # --- Graphique 2 : convergence en log-log ---
    st.subheader(t("hedging_convergence"))

    reference = [ecarts[0] * np.sqrt(frequences[0] / n) for n in frequences]

    fig_conv = go.Figure()

    fig_conv.add_trace(go.Scatter(
        x=frequences, y=ecarts, mode="lines+markers",
        name=t("legend_observed"),
        line=dict(width=3, color="#4C9BE8"),
        marker=dict(size=9),
    ))

    fig_conv.add_trace(go.Scatter(
        x=frequences, y=reference, mode="lines",
        name=t("legend_theory"),
        line=dict(width=2, color="#E8574C", dash="dash"),
    ))

    fig_conv.update_layout(
        template="plotly_dark",
        xaxis_title=t("axis_rebalancings"),
        yaxis_title=t("axis_std"),
        xaxis=dict(type="log", tickmode="array", tickvals=frequences,
                   ticktext=[str(n) for n in frequences]),
        yaxis_type="log",
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    )

    st.plotly_chart(fig_conv, width="stretch")
    st.caption(t("caption_convergence"))



# ---------------------------------------------------------------------------
# Pied de page
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="footer">
    Built by <strong>Yaniv C.</strong> &nbsp;|&nbsp;
    <a href="https://linkedin.com/in/yaniv-cukierman-b384a139b/" target="_blank">LinkedIn</a><br>
    Market data via Yahoo Finance (delayed ~15 min)
</div>
""",
    unsafe_allow_html=True,
)
