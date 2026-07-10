"""Crypto prediction and trend analysis service (async, dependency-gated)."""

import asyncio
import logging
from datetime import timedelta
from typing import Any

import numpy as np

from app.core.cache import get_cache
from app.core.config import Settings
from app.core.exceptions import ServiceError
from app.core.log import get_logger

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

logger = get_logger(__name__)

_prophet_semaphore: asyncio.Semaphore | None = None

def _get_prophet_semaphore() -> asyncio.Semaphore:
    global _prophet_semaphore
    if _prophet_semaphore is None:
        _prophet_semaphore = asyncio.Semaphore(2)
    return _prophet_semaphore


class CryptoService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pd = None
        self._prophet = None
        self._yf = None
        self._rust_predictor = None

    def _get_pd(self):
        if self._pd is None:
            try:
                import pandas as pd

                self._pd = pd
            except Exception as e:
                raise ServiceError("pandas library is not available") from e
        return self._pd

    def _get_yf(self):
        if self._yf is None:
            try:
                import yfinance as yf

                self._yf = yf
            except Exception as e:
                raise ServiceError("yfinance library is not available") from e
        return self._yf

    def _get_prophet(self):
        if self._prophet is None:
            try:
                from prophet import Prophet

                self._prophet = Prophet
            except Exception:
                logger.warning("Prophet not available — predictions will be degraded")
                self._prophet = False
        return self._prophet if self._prophet is not False else None

    def _get_rust_predictor(self):
        if self._rust_predictor is None:
            try:
                import rust_predictor

                if hasattr(rust_predictor, "train_and_predict"):
                    self._rust_predictor = rust_predictor
                else:
                    logger.warning("rust_predictor native module not compiled — predictions will be degraded")
                    self._rust_predictor = False
            except Exception:
                logger.warning("rust_predictor not available — predictions will be degraded")
                self._rust_predictor = False
        return self._rust_predictor if self._rust_predictor is not False else None

    async def predict(self, symbol: str = "BTC-USD") -> dict:
        cache = get_cache()
        cached = cache.get(f"predict:{symbol}")
        if cached:
            return cached

        result = await self._run_analysis(symbol, period="1y", lookback=20, rust_epochs=150)
        cache.set(f"predict:{symbol}", result, ttl=300)
        return result

    async def analyze_trend(self, symbol: str = "BTC-USD") -> dict:
        cache = get_cache()
        cached = cache.get(f"trend:{symbol}")
        if cached:
            return cached

        result = await self._run_analysis(symbol, period="4mo", lookback=15, rust_epochs=100, include_ta=True)
        cache.set(f"trend:{symbol}", result, ttl=300)
        return result

    async def _run_analysis(
        self,
        symbol: str,
        period: str,
        lookback: int,
        rust_epochs: int,
        include_ta: bool = False,
    ) -> dict:
        loop = asyncio.get_running_loop()

        def _download():
            yf = self._get_yf()
            df = yf.download(symbol, period=period, interval="1d", progress=False)
            if df.empty:
                msg = f"Symbol '{symbol}' not found or no data available"
                raise ServiceError(msg)
            return df

        df = await loop.run_in_executor(None, _download)
        df = df.dropna()
        if df.empty:
            msg = f"No valid data after cleaning for symbol '{symbol}'"
            raise ServiceError(msg)
        pd = self._get_pd()

        close_prices = df["Close"][symbol].values if isinstance(df.columns, pd.MultiIndex) else df["Close"].values

        timestamps = df.index.strftime("%Y-%m-%d").tolist()
        min_points = 50 if include_ta else 30
        if len(close_prices) < min_points:
            msg = f"Not enough data for symbol '{symbol}'"
            raise ServiceError(msg)

        future_days = 7
        degraded = []

        def _run_prophet():
            prophet_mod = self._get_prophet()
            if prophet_mod is None:
                return None
            prophet_df = pd.DataFrame(
                {
                    "ds": pd.to_datetime(df.index.tz_localize(None) if df.index.tz is not None else df.index),
                    "y": close_prices,
                }
            )
            m = prophet_mod(daily_seasonality=True, yearly_seasonality=True)
            m.fit(prophet_df)
            future = m.make_future_dataframe(periods=future_days)
            forecast = m.predict(future)
            return forecast["yhat"].tail(future_days).values.tolist()

        def _run_rust():
            predictor = self._get_rust_predictor()
            if predictor is None:
                return None
            return predictor.train_and_predict(
                close_prices.tolist(),
                lookback,
                rust_epochs,
                future_days,
            )

        async def _run_prophet_async():
            sem = _get_prophet_semaphore()
            try:
                await asyncio.wait_for(sem.acquire(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Prophet prediction timeout for {symbol}: Too many concurrent models")
                return None
            try:
                return await loop.run_in_executor(None, _run_prophet)
            finally:
                sem.release()

        prophet_preds = await _run_prophet_async()
        rust_preds = await loop.run_in_executor(None, _run_rust)

        if prophet_preds is None and rust_preds is None:
            raise ServiceError("No prediction engine available (requires Prophet or rust_predictor)")

        if prophet_preds is None:
            prophet_preds = [None] * future_days
            degraded.append("prophet")
        if rust_preds is None:
            rust_preds = [None] * future_days
            degraded.append("rust_predictor")

        last_date = df.index[-1]
        future_dates = [(last_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, future_days + 1)]

        degraded_flag = degraded if degraded else None

        if include_ta:
            result = await loop.run_in_executor(
                None, self._build_trend_result,
                symbol, close_prices, timestamps, future_dates, prophet_preds, rust_preds, df,
            )
            if degraded_flag:
                result["degraded"] = degraded_flag
            return result

        history = [{"date": d, "price": float(p)} for d, p in zip(timestamps, close_prices, strict=True)]
        future_data = []
        for date, p_val, r_val in zip(future_dates, prophet_preds, rust_preds, strict=True):
            entry = {"date": date}
            if p_val is not None:
                entry["prophet_price"] = float(p_val)
            if r_val is not None:
                entry["rust_price"] = float(r_val)
            future_data.append(entry)

        result = {"symbol": symbol, "history": history, "predictions": future_data}
        if degraded_flag:
            result["degraded"] = degraded_flag
        return result

    def _compute_ta(self, close_prices: np.ndarray, df_index) -> Any:
        pd = self._get_pd()
        df_ta = pd.DataFrame({"Close": close_prices}, index=df_index)

        df_ta["SMA20"] = df_ta["Close"].rolling(window=20).mean()
        df_ta["SMA50"] = df_ta["Close"].rolling(window=50).mean()

        delta = df_ta["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_ta["RSI"] = 100 - (100 / (1 + rs))

        exp1 = df_ta["Close"].ewm(span=12, adjust=False).mean()
        exp2 = df_ta["Close"].ewm(span=26, adjust=False).mean()
        df_ta["MACD"] = exp1 - exp2
        df_ta["Signal"] = df_ta["MACD"].ewm(span=9, adjust=False).mean()
        df_ta["MACD_Hist"] = df_ta["MACD"] - df_ta["Signal"]
        df_ta = df_ta.fillna(0)

        return df_ta

    def _build_trend_result(
        self,
        symbol: str,
        close_prices,
        timestamps,
        future_dates,
        prophet_preds,
        rust_preds,
        df,
    ) -> dict:
        df_ta = self._compute_ta(close_prices, df.index)

        history = []
        for i in range(len(timestamps)):
            history.append(
                {
                    "date": timestamps[i],
                    "price": float(close_prices[i]),
                    "sma20": float(df_ta["SMA20"].iloc[i]),
                    "sma50": float(df_ta["SMA50"].iloc[i]),
                    "rsi": float(df_ta["RSI"].iloc[i]),
                    "macd": float(df_ta["MACD"].iloc[i]),
                    "macd_hist": float(df_ta["MACD_Hist"].iloc[i]),
                }
            )

        future_data = []
        for d, p, r in zip(future_dates, prophet_preds, rust_preds, strict=True):
            future_data.append({"date": d, "prophet_price": float(p), "rust_price": float(r)})

        curr_price = float(close_prices[-1])
        curr_rsi = float(df_ta["RSI"].iloc[-1])
        curr_sma20 = float(df_ta["SMA20"].iloc[-1])
        proj_rs_price = rust_preds[-1]

        score = 0
        if curr_rsi < 40:
            score += 1
        elif curr_rsi > 70:
            score -= 1

        if curr_price > curr_sma20:
            score += 1
        else:
            score -= 1

        if proj_rs_price > curr_price * 1.025:
            score += 2
        elif proj_rs_price > curr_price * 1.005:
            score += 1
        elif proj_rs_price < curr_price * 0.975:
            score -= 2
        elif proj_rs_price < curr_price * 0.995:
            score -= 1

        if score >= 3:
            verdict = "Strong Bullish"
        elif score >= 1:
            verdict = "Bullish"
        elif score == 0:
            verdict = "Neutral"
        elif score >= -2:
            verdict = "Bearish"
        else:
            verdict = "Strong Bearish"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "score": score,
            "current_metrics": {"price": curr_price, "rsi": curr_rsi, "sma20": curr_sma20},
            "history": history,
            "predictions": future_data,
        }
