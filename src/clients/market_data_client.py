from __future__ import annotations

from datetime import datetime

import yfinance as yf

from src.models.schemas import PriceSnapshot

try:
    import akshare as ak
except ImportError:  # pragma: no cover
    ak = None


class MarketDataClient:
    def get_price_snapshot(self, symbol: str) -> PriceSnapshot:
        try:
            return self._from_yfinance(symbol)
        except Exception:
            if symbol.endswith(".HK"):
                return self._from_akshare(symbol)
            raise

    def _from_yfinance(self, symbol: str) -> PriceSnapshot:
        history = yf.Ticker(symbol).history(period="1mo", interval="1d")
        if history.empty or len(history) < 2:
            raise RuntimeError(f"No price history available for {symbol}")

        latest = history.iloc[-1]
        previous = history.iloc[-2]
        avg_20d_volume = float(history["Volume"].tail(20).mean()) if "Volume" in history else 0.0
        previous_close = float(previous["Close"])
        change_pct = 0.0 if previous_close == 0 else ((float(latest["Close"]) - previous_close) / previous_close) * 100
        return PriceSnapshot(
            symbol=symbol,
            as_of=datetime.utcnow(),
            close=float(latest["Close"]),
            change_pct=change_pct,
            volume=float(latest.get("Volume", 0.0)),
            avg_20d_volume=avg_20d_volume,
            source="yfinance",
        )

    def _from_akshare(self, symbol: str) -> PriceSnapshot:
        if ak is None:
            raise RuntimeError("akshare is not installed for HK fallback")

        hk_symbol = symbol.replace(".HK", "")
        history = ak.stock_hk_hist(symbol=hk_symbol, period="daily", adjust="")
        if history.empty or len(history) < 2:
            raise RuntimeError(f"No akshare price history available for {symbol}")

        latest = history.iloc[-1]
        previous = history.iloc[-2]
        avg_20d_volume = float(history["成交量"].tail(20).mean()) if "成交量" in history else 0.0
        previous_close = float(previous["收盘"])
        change_pct = 0.0 if previous_close == 0 else ((float(latest["收盘"]) - previous_close) / previous_close) * 100
        return PriceSnapshot(
            symbol=symbol,
            as_of=datetime.utcnow(),
            close=float(latest["收盘"]),
            change_pct=change_pct,
            volume=float(latest.get("成交量", 0.0)),
            avg_20d_volume=avg_20d_volume,
            source="akshare",
        )
