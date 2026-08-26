# Options Pricer — Black-Scholes, Monte Carlo & Implied Volatility
 
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?logo=scipy&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
 
An interactive options pricing engine built from scratch in Python, connected to
live market data. Prices European and American options through three independent
methods, computes the full set of Greeks, and reconstructs the implied volatility
smile from real quoted option prices.
 
**[▶ Live demo](#)** · Built by Yaniv C. · [LinkedIn](https://linkedin.com/in/yaniv-cukierman-b384a139b/)
 
![Volatility smile](smile_volatilite.png)
 
---
 
## Why this project
 
Anyone can say they are interested in derivatives. This project is an attempt to
actually understand how options are priced — by implementing the models rather
than reading about them, validating every result against a known identity, and
then confronting the theoretical output with what the market actually quotes.
 
The most interesting outcome is not that the pricer works. It is *where it fails*:
the volatility smile above is a direct, empirical demonstration that the core
assumption of Black-Scholes does not hold.
 
---
 
## Features
 
### Pricing methods
 
- **Black-Scholes** — closed-form solution for European calls and puts
- **Monte Carlo** — 100,000 simulated paths under the risk-neutral measure
- **Binomial tree (CRR)** — 500 steps, European *and* American exercise
### Risk metrics
 
Delta, Gamma, Vega, Theta and Rho, from analytical formulas and expressed in
market conventions — Theta per calendar day, Vega and Rho per volatility or
rate point rather than per unit.
 
### Implied volatility
 
- Newton-Raphson inversion of the Black-Scholes formula
- Automatic fallback to Brent's method when Newton-Raphson diverges — vega
  approaches zero for deep ITM/OTM options, which makes the Newton step explode
- Volatility smile rebuilt from out-of-the-money contracts only (puts below
  spot, calls above), the standard approach on a trading desk
- 3D implied volatility surface across multiple expiries
### Market data
 
- Live spot prices and option chains via `yfinance`
- Historical volatility from log returns, annualised over 252 trading days
- Works on any US-listed underlying
---
 
## Validation
 
Every pricing method is checked against an identity that *must* hold if the
implementation is correct — not against my own expectations.
 
| Test | Expected | Result (AAPL, 30d, ATM) |
|:---|:---|:---|
| Put-call parity — `C - P = S - K·e^(-rT)` | exact | ✅ holds |
| Monte Carlo vs Black-Scholes | convergence | 0.022 absolute gap |
| Binomial (European) vs Black-Scholes | convergence | 0.0006 absolute gap |
| Rho identity — `ρ_call - ρ_put = K·T·e^(-rT)` | exact | ✅ holds |
| Implied vol round-trip — `BS(σ_implied) = market price` | exact | 8.7999999999 vs 8.80 |
| Early exercise premium (American put) | ≥ 0 | +0.047 |
 
The binomial tree converges an order of magnitude closer than Monte Carlo at
comparable settings — expected, since it is deterministic rather than sampled.
 
---
 
## What the model gets wrong
 
Black-Scholes assumes a single constant volatility per underlying. If that were
true, implied volatility would be identical across all strikes for a given
expiry — a flat line.
 
It is not. On AAPL 30-day options, implied volatility runs from **~31% at low
strikes** down to **~24% near the money**, then rises again for high strikes.
This skew reflects the premium investors pay for downside protection, a
structural feature of equity markets since 1987.
 
Three further limitations worth stating plainly:
 
| Limitation | Consequence |
|:---|:---|
| Dividends are not modelled | Small but systematic bias in AAPL call prices |
| American calls priced as European | Correct without dividends; wrong for a dividend payer |
| Market data delayed ~15 min | Fine for analysis, unusable for execution |
 
The early-exercise premium becomes economically significant for deep
in-the-money American puts. On a long-dated example (S=250, K=350, 550 days),
the binomial tree prices the American put **8.6% above** its European
equivalent — a gap Black-Scholes cannot capture by construction.
 
---
 
## Running locally
 
```bash
git clone https://github.com/yaniv-cuki/option-pricer.git
cd option-pricer
 
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
 
pip install -r requirements.txt
streamlit run app.py
```
 
To run the pricing engine on its own, without the interface:
 
```bash
python3 pricer.py
```
 
---
 
## Project structure
 
```
option-pricer/
├── pricer.py           # Pricing engine: models, Greeks, implied vol
├── app.py              # Streamlit dashboard
├── traductions.py      # UI strings (EN / FR)
├── requirements.txt
└── .streamlit/
    └── config.toml     # Theme
```
 
The pricing logic is deliberately kept independent of the interface: `pricer.py`
has no Streamlit dependency and can be imported into a notebook or a test suite.
 
---
 
## Stack
 
Python · NumPy · SciPy · pandas · yfinance · Plotly · Streamlit
 
---
 
## Possible extensions
 
- Delta-hedging simulation — P&L of a discretely rebalanced hedge
- SVI parameterisation to fit and smooth the volatility surface
- Dividend-adjusted pricing
- Multi-leg strategies (straddles, spreads) with aggregated Greeks
