from __future__ import annotations

from datetime import datetime
from typing import Any

from src.models.schemas import PriceSnapshot


class FutuMarketDataClient:
    """Fetch price snapshots through a local Futu OpenD quote gateway."""

    def __init__(self, host: str = "127.0.0.1", port: int = 11111) -> None:
        try:
            from futu import OpenQuoteContext, RET_OK
        except ImportError as exc:  # pragma: no cover - depends on optional SDK
            raise RuntimeError("futu-api is not installed. Run: pip install futu-api") from exc

        self._ret_ok = RET_OK
        self._quote_ctx = OpenQuoteContext(host=host, port=int(port))

    def close(self) -> None:
        """Close the OpenD quote connection to avoid exhausting local sessions."""
        self._quote_ctx.close()

    def get_price_snapshot(self, symbol: str) -> PriceSnapshot:
        """Return the latest Futu market snapshot for a US or HK symbol."""
        futu_code = to_futu_code(symbol)
        ret, data = self._quote_ctx.get_market_snapshot([futu_code])
        if ret != self._ret_ok:
            raise RuntimeError(f"Futu snapshot failed for {symbol}: {_safe_error(data)}")
        if data.empty:
            raise RuntimeError(f"Futu returned an empty snapshot for {symbol}")

        row = data.iloc[0].to_dict()
        close = _number(row, "last_price")
        previous_close = _number(row, "prev_close_price", default=0.0)
        volume = _number(row, "volume", default=0.0)
        volume_ratio = _number(row, "volume_ratio", default=0.0)
        avg_20d_volume = volume / volume_ratio if volume_ratio > 0 else 0.0
        change_pct = 0.0 if previous_close == 0 else ((close - previous_close) / previous_close) * 100

        return PriceSnapshot(
            symbol=symbol,
            as_of=_parse_snapshot_time(row.get("update_time")),
            close=close,
            change_pct=change_pct,
            volume=volume,
            avg_20d_volume=avg_20d_volume,
            source="futu",
        )


def to_futu_code(symbol: str) -> str:
    """Convert AlphaX/yfinance style symbols into Futu OpenAPI codes."""
    normalized = symbol.strip().upper()
    if normalized.startswith(("US.", "HK.", "SH.", "SZ.")):
        return normalized
    if normalized.endswith(".HK"):
        return f"HK.{normalized.removesuffix('.HK').zfill(5)}"
    if normalized.startswith(("^", ".")):
        raise ValueError(f"Futu code mapping is not configured for benchmark/index symbol: {symbol}")
    return f"US.{normalized}"


def _number(row: dict[str, Any], key: str, default: float | None = None) -> float:
    value = row.get(key, default)
    if value is None:
        if default is None:
            raise RuntimeError(f"Futu snapshot is missing required field: {key}")
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Futu snapshot field {key} is not numeric: {value!r}") from exc


def _parse_snapshot_time(value: Any) -> datetime:
    if not value:
        return datetime.utcnow()
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _safe_error(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ")
    return text[:240]
