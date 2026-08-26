# Options Pricer — Black-Scholes, Monte Carlo & Implied Volatility
 
An interactive options pricing engine built from scratch in Python, connected to
live market data. Prices European and American options through three independent
methods, computes the full set of Greeks, and reconstructs the implied volatility
smile from real quoted option prices.
 
**[Live demo](#)** · Built by Yaniv C. · [LinkedIn](https://linkedin.com/in/yaniv-cukierman-b384a139b/)
 
![Volatility smile](smile_volatilite.png)
 
---
 
## Why this project
 
Anyone can say they are interested in derivatives. This project is an attempt to
actually understand how options are priced — by implementing the models rather
than reading about them, validating every result against a known identity, and
then confronting the theoretical output with what the market actually quotes.
 
The most interesting outcome is not that the pricer works. It is *where it fails*:
the volatility smile below is a direct, empirical demonstration that the core
assumption of Black-Scholes does not hold.
 
---
 
## Features
 
**Pricing methods**
- Black-Scholes closed-form solution (European calls and puts)
- Monte Carlo simulation (100,000 paths, risk-neutral measure)
- Cox-Ross-Rubinstein binomial tree (500 steps, European and American exercise)
**Risk metrics**
- Delta, Gamma, Vega, Theta, Rho — analytical formulas, market conventions
  (Theta per day, Vega and Rho per volatility/rate point)
**Implied volatility**
- Newton-Raphson inversion of Black-Scholes
- Automatic fallback to Brent's method when Newton-Raphson diverges
  (vega approaches zero for deep ITM/OTM options)
- Volatility smile reconstruction from out-of-the-money contracts
- 3D implied volatility surface across multiple expiries
**Market data**
- Live spot prices and option chains via `yfinance`
- Historical volatility computed from log returns (252 trading days)
- Any US-listed underlying
---
 
## Validation
 
Every pricing method is checked against an identity that must hold if the
implementation is correct — not against my own expectations.
 
| Test | Expected | Result (AAPL, 30d, ATM) |
|---|---|---|
| Put-call parity: `C - P = S - K·e^(-rT)` | exact | ✅ holds |
| Monte Carlo vs Black-Scholes | convergence | 0.022 absolute gap |
| Binomial (European) vs Black-Scholes | convergence | 0.0006 absolute gap |
| Rho identity: `ρ_call - ρ_put = K·T·e^(-rT)` | exact | ✅ holds |
| Implied vol round-trip: `BS(σ_implied) = market price` | exact | 8.7999999999 vs 8.80 |
| Early exercise premium (American put) | ≥ 0 | +0.047 |
 
The binomial tree converges an order of magnitude closer than Monte Carlo at
comparable settings — expected, since it is deterministic rather than sampled.
 
---
 
## What the model gets wrong
 
Black-Scholes assumes a single constant volatility per underlying. If that were
true, implied volatility would be identical across all strikes for a given
expiry — a flat line.
 
It is not. On AAPL 30-day options, implied volatility runs from ~31% at low
strikes down to ~24% near the money, then rises again for high strikes. This
skew reflects the premium investors pay for downside protection, a structural
feature of equity markets since 1987.
 
Two further limitations worth noting:
- **Dividends are not modelled.** For AAPL this introduces a small but
  systematic bias in call prices.
- **American calls are priced as European.** This is correct without dividends
  (early exercise is never optimal), but would be wrong for a dividend-paying
  underlying.
- **Market data is delayed ~15 minutes** (free Yahoo Finance feed). Fine for
  analysis, unusable for execution.
The early-exercise premium becomes economically significant for deep
in-the-money American puts: on a long-dated example (S=250, K=350, 550 days),
the binomial tree prices the American put 8.6% above its European equivalent —
a gap Black-Scholes cannot capture by construction.
 
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
 
- Delta-hedging simulation (P&L of a discretely rebalanced hedge)
- SVI parameterisation to fit and smooth the volatility surface
- Dividend-adjusted pricing
- Multi-leg strategies (straddles, spreads) with aggregated Greeks
