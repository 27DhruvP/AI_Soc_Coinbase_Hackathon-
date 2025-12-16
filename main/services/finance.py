"""Finance data utilities.

This app uses yfinance as a lightweight market data source.

Notes:
* yfinance is not an official data provider. Treat numbers as approximate.
* This module is intentionally dependency-light (no TA libraries).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass
class StockSnapshot:
    ticker: str
    name: str | None
    currency: str | None
    price: float | None
    change_pct: float | None
    market_cap: int | None
    pe: float | None
    forward_pe: float | None
    eps: float | None
    dividend_yield: float | None
    beta: float | None
    sector: str | None
    industry: str | None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float, np.number)):
            return float(x)
        # Sometimes yfinance returns "N/A" strings.
        s = str(x).strip()
        if not s or s.lower() in {"nan", "none", "n/a", "na"}:
            return None
        return float(s)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, np.integer)):
            return int(x)
        f = _safe_float(x)
        return int(f) if f is not None else None
    except Exception:
        return None


@lru_cache(maxsize=128)
def get_ticker(ticker: str) -> yf.Ticker:
    return yf.Ticker(ticker)


def get_snapshot(ticker: str) -> StockSnapshot:
    t = get_ticker(ticker)

    # yfinance fields can vary across tickers/markets.
    info: Dict[str, Any] = {}
    try:
        info = t.get_info() or {}
    except Exception:
        info = {}

    # Prefer fast_info for latest price when available.
    price = None
    currency = info.get("currency")
    try:
        fi = getattr(t, "fast_info", None)
        if fi:
            price = _safe_float(getattr(fi, "last_price", None) or fi.get("last_price"))
            currency = currency or getattr(fi, "currency", None) or fi.get("currency")
    except Exception:
        pass

    # Fallback.
    price = price or _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))

    prev_close = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
    change_pct = None
    if price is not None and prev_close:
        change_pct = (price - prev_close) / prev_close * 100.0

    dy = _safe_float(info.get("dividendYield"))
    if dy is not None:
        dy *= 100.0  # display as percent

    return StockSnapshot(
        ticker=ticker.upper(),
        name=info.get("shortName") or info.get("longName"),
        currency=currency,
        price=price,
        change_pct=change_pct,
        market_cap=_safe_int(info.get("marketCap")),
        pe=_safe_float(info.get("trailingPE")),
        forward_pe=_safe_float(info.get("forwardPE")),
        eps=_safe_float(info.get("trailingEps")),
        dividend_yield=dy,
        beta=_safe_float(info.get("beta")),
        sector=info.get("sector"),
        industry=info.get("industry"),
    )


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Get OHLCV history.

    Returns a dataframe with columns: Open, High, Low, Close, Volume.
    """
    t = get_ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    # Standardize column names.
    df = df.rename(columns={c: c.title() for c in df.columns})
    return df


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def technical_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute a small set of technical indicators for UI + LLM context."""
    if df is None or df.empty or "Close" not in df.columns:
        return {"error": "No price history available."}

    close = df["Close"].astype(float)
    out: Dict[str, Any] = {}

    out["sma_20"] = _safe_float(sma(close, 20).iloc[-1])
    out["sma_50"] = _safe_float(sma(close, 50).iloc[-1])
    out["rsi_14"] = _safe_float(rsi(close, 14).iloc[-1])
    macd_line, signal_line, hist = macd(close)
    out["macd"] = _safe_float(macd_line.iloc[-1])
    out["macd_signal"] = _safe_float(signal_line.iloc[-1])
    out["macd_hist"] = _safe_float(hist.iloc[-1])
    out["volatility_30d_pct"] = _safe_float(close.pct_change().rolling(30).std().iloc[-1] * np.sqrt(252) * 100)
    return out


def sma_crossover_backtest(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> Dict[str, Any]:
    """Tiny toy backtest: long when SMA_fast > SMA_slow.

    This is intentionally simple and is framed as educational.
    """
    if df is None or df.empty or "Close" not in df.columns:
        return {"error": "No price history available."}
    close = df["Close"].astype(float)
    fast_sma = sma(close, fast)
    slow_sma = sma(close, slow)
    signal = (fast_sma > slow_sma).astype(int)
    returns = close.pct_change().fillna(0)
    strat = returns * signal.shift(1).fillna(0)
    equity = (1 + strat).cumprod()
    buyhold = (1 + returns).cumprod()

    def _ann_return(eq: pd.Series) -> Optional[float]:
        if eq.empty:
            return None
        days = len(eq)
        if days < 2:
            return None
        total = float(eq.iloc[-1])
        years = days / 252.0
        if years <= 0:
            return None
        return (total ** (1 / years) - 1) * 100

    dd = (equity / equity.cummax() - 1).min() * 100
    out = {
        "strategy_total_return_pct": _safe_float((equity.iloc[-1] - 1) * 100),
        "strategy_annualized_return_pct": _safe_float(_ann_return(equity)),
        "strategy_max_drawdown_pct": _safe_float(dd),
        "buyhold_total_return_pct": _safe_float((buyhold.iloc[-1] - 1) * 100),
        "buyhold_annualized_return_pct": _safe_float(_ann_return(buyhold)),
    }
    return out
