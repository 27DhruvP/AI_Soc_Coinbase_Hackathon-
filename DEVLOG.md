# Devlog: 

This log tells the story of turning the original “5-word summariser” miniapp into a finance-focused assistant that combines:

* **Market data** via `yfinance` (quotes, fundamentals, history)
* **Lightweight analytics** (RSI, SMA, MACD, volatility)
* **A generative model** via OpenRouter (configurable)
* **A much nicer UI** (single-page chat + toggles)

> Disclaimer baked into the product: this is educational tooling, not financial advice.

---

## 1) Baseline audit

The starting project was a small Django app with:

* `home.html` containing a text box + a submit button
* a `/process-name/` endpoint that forwarded the text to OpenRouter and returned a 5-word summary
* Farcaster miniapp manifest + webhook endpoints

The architecture was good for rapid iteration (Django + a single template), but the “business logic” (LLM call) lived directly inside the view, and the UI had no room for richer features.

---

## 2) Product goal

Build a “financial investment advice bot” experience while keeping it responsible:

* It should **never** claim to be a licensed advisor.
* It should provide **frameworks**, options, and risk sizing rather than “BUY/SELL NOW”.
* It should show the user what data it used (snapshot + indicators) so it feels inspectable.

---

## 3) New features added

### 3.1 Data layer (yfinance)

Created `main/services/finance.py`:

* `get_snapshot(ticker)` for fundamentals and basic quote info
* `get_history(ticker, period="1y")` for price history
* indicator functions:
  * SMA(20/50)
  * RSI(14)
  * MACD(12/26/9)
  * 30-day annualized volatility (rough)
* `sma_crossover_backtest()` as an explicitly **toy** backtest (educational)

Caching (`lru_cache`) is used for the `yf.Ticker` object to reduce repeated lookups during chat.

### 3.2 LLM wrapper

Created `main/services/llm.py`:

* Centralizes the OpenRouter call
* Reads config from env vars
* Provides a graceful fallback message when the API key is missing

### 3.3 Safety / guardrails

Created `main/services/prompts.py` with an `INVESTMENT_SYSTEM_PROMPT` that forces:

* a short disclaimer
* uncertainty and caveats
* follow-up questions when key info is missing
* structured answers

Also added a UI toggle called **Guardrails** to control a small extra “tone reminder”.

### 3.4 New API endpoints

Updated `main/views.py`:

* `GET /api/snapshot/?ticker=...`
* `POST /api/chat/` which:
  1) accepts `{ message, ticker, settings }`
  2) optionally pulls yfinance data based on toggles
  3) injects the data as JSON context to the LLM
  4) returns `{ reply, snapshot, technicals, backtest }`

Updated `main/urls.py` accordingly.

### 3.5 UI overhaul

Replaced `home.html` with a finance-themed single-page UI:

* Split layout: **Controls + Snapshot** on the left, **Chat** on the right
* “Load snapshot” button to fetch data without chatting
* Toggles the user can switch on/off:
  * Fundamentals
  * Technicals
  * Toy backtest
  * Guardrails
* Chat log with message bubbles and context metadata
* Clear chat button

This keeps the project “one template” simple, but the experience now feels like an actual app.

---

## 4) Dependency changes

Updated `requirements.txt` to include:

* `yfinance`
* `pandas`
* `numpy`

---

## 5) How to run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# LLM (optional but recommended)
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="openai/gpt-4o-mini"  # optional

python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

If the API key is missing, the bot still works as a data dashboard, but the “narrative” reply will explain that the LLM is not configured.

---

## 6) Things to improve next

If you want to keep leveling it up:

* Add **conversation memory** (store last N messages in session) so follow-ups feel continuous.
* Add **ETF comparison mode** (two tickers, side-by-side snapshot + risk stats).
* Add **user profile** (risk tolerance, horizon, region) so the bot can default to better assumptions.
* Add **rate limiting + caching** in production.
* Add **unit tests** for indicators and backtest calculations.

---

## 7) Philosophy (aka: the vibe)

Markets are a chaotic orchestra. FinChat doesn’t pretend to be the conductor. It hands you sheet music, points out where the tempo changes, and reminds you that sometimes the loudest cymbal crash is just… noise.
