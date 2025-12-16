
Django miniapp that combines **yfinance** market data with a **generative model** (via OpenRouter) to provide educational, decision-support style investing guidance.

## Run

```bash
pip install -r requirements.txt

# optional (enables LLM responses)
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="openai/gpt-4o-mini"  # optional

python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## API

* `GET /api/snapshot/?ticker=AAPL`
* `POST /api/chat/` JSON body:

```json
{
  "ticker": "AAPL",
  "message": "Is this a sensible long-term hold?",
  "settings": {"fundamentals": true, "technicals": true, "backtest": false, "guardrails": true}
}
```

## Important

This project is for **education** and **experimentation**. It is not financial advice. Data from yfinance is unofficial.

See `DEVLOG.md` for the full build story.
