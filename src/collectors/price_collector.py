from __future__ import annotations

from src.clients.market_data_client import MarketDataClient
from src.models.schemas import PriceSnapshot
from src.utils.io import write_json


def collect_prices(symbols: list[str], settings: dict, logger) -> dict[str, PriceSnapshot]:
    client = MarketDataClient(settings=settings, logger=logger)
    snapshots: dict[str, PriceSnapshot] = {}
    raw_payload: list[dict] = []

    try:
        for symbol in sorted(set(symbols)):
            try:
                snapshot = client.get_price_snapshot(symbol)
                snapshots[symbol] = snapshot
                raw_payload.append({"symbol": symbol, "snapshot": snapshot})
            except Exception as exc:
                logger.warning("price fetch failed for %s: %s", symbol, exc)
    finally:
        client.close()

    report_date = settings.get("_run_date")
    output_path = f'{settings["paths"]["raw_prices_dir"]}/{report_date}.json'
    write_json(output_path, raw_payload)
    logger.info("collected prices for %s symbols", len(snapshots))
    return snapshots
