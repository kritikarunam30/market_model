from pathlib import Path
import logging
import os
import random
import time
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s.", name, raw, default)
        return default
    return max(value, minimum)


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s.", name, raw, default)
        return default
    return max(value, minimum)


def _retry_delay(attempt: int, base_sleep_seconds: float, jitter_seconds: float) -> float:
    return base_sleep_seconds * attempt + random.uniform(0.0, jitter_seconds)

MARKET_CONFIG = {
    "india": {
        "equity": ["^NSEI"],
        "vix": ["^INDIAVIX"],
        "fx": ["INR=X"],
        "bond": ["^IN10YB", "IN10Y.B"],
        "commodity": ["GC=F"],
    },
    "us": {
        "equity": ["^GSPC"],
        "vix": ["^VIX"],
        "fx": ["DX-Y.NYB"],
        "bond": ["^TNX"],
        "commodity": ["CL=F"],
    },
    "uk": {
        "equity": ["^FTSE"],
        "vix": ["^VFTSE"],
        "fx": ["GBPUSD=X"],
        "bond": ["^UK10YB"],
        "commodity": ["BZ=F"],
    },
    "japan": {
        "equity": ["^N225"],
        "vix": ["^VNKY"],
        "fx": ["JPY=X"],
        "bond": ["^JP10Y", "^JP10YB"],
        "commodity": ["GC=F"],
    },
    "china": {
        "equity": ["000001.SS"],
        "vix": [],
        "fx": ["CNY=X"],
        "bond": ["CGB"],
        "commodity": ["HG=F"],
    },
    "germany": {
        "equity": ["^GDAXI"],
        "vix": ["^VDAX-NEW"],
        "fx": ["EURUSD=X"],
        "bond": ["^DE10YB"],
        "commodity": ["NG=F"],
    },
    "hong_kong": {
        "equity": ["^HSI"],
        "vix": ["^VHSI"],
        "fx": ["HKD=X"],
        "bond": ["^HK10YB"],
        "commodity": ["SI=F"],
    },
}

DATA_PATH = Path("data/market_data.csv")

LEGACY_ALIAS_MAP = {
    "india": "india_equity_close",
    "india_vix": "india_vix_close",
    "fx": "india_fx_close",
    "us": "us_equity_close",
    "global_vix": "us_vix_close",
}


def _collect_all_tickers() -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()

    for market_signals in MARKET_CONFIG.values():
        for candidates in market_signals.values():
            for ticker in candidates:
                if ticker and ticker not in seen:
                    seen.add(ticker)
                    tickers.append(ticker)

    return tickers


def _extract_close_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"].copy()
        elif "Adj Close" in raw.columns.get_level_values(0):
            close = raw["Adj Close"].copy()
        else:
            return pd.DataFrame(index=raw.index)

        if isinstance(close, pd.Series):
            close = close.to_frame()
        return close

    # Single ticker responses can be returned as a flat frame.
    if "Close" in raw.columns:
        return raw[["Close"]].rename(columns={"Close": "single_ticker"})
    if "Adj Close" in raw.columns:
        return raw[["Adj Close"]].rename(columns={"Adj Close": "single_ticker"})

    return pd.DataFrame(index=raw.index)


def _build_market_frame(close: pd.DataFrame) -> pd.DataFrame:
    market_data = pd.DataFrame(index=close.index)
    missing_series: list[str] = []

    for market, signals in MARKET_CONFIG.items():
        for signal, candidates in signals.items():
            column_name = f"{market}_{signal}_close"
            selected = None

            for ticker in candidates:
                if not ticker:
                    continue
                if ticker in close.columns and close[ticker].notna().any():
                    selected = ticker
                    break

            if selected is None:
                missing_series.append(column_name)
                continue

            market_data[column_name] = close[selected]

    if missing_series:
        logger.warning(
            "Missing or unavailable market series skipped: %s",
            ", ".join(missing_series),
        )

    for legacy_name, canonical_name in LEGACY_ALIAS_MAP.items():
        if canonical_name in market_data.columns:
            market_data[legacy_name] = market_data[canonical_name]

    return market_data


def _download_close_in_batches(
    tickers: list[str],
    start: str,
    end: str | None,
    batch_size: int = 4,
    max_retries: int = 4,
    base_sleep_seconds: float = 2.0,
    jitter_seconds: float = 0.75,
) -> tuple[pd.DataFrame, list[str]]:
    close_frames: list[pd.DataFrame] = []
    failed_tickers: list[str] = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        batch_close = pd.DataFrame()

        for attempt in range(1, max_retries + 1):
            try:
                raw = yf.download(
                    batch,
                    start=start,
                    end=end,
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )
            except Exception as exc:
                wait_seconds = _retry_delay(attempt, base_sleep_seconds, jitter_seconds)
                logger.warning(
                    "Batch %s failed on attempt %s/%s: %s. Retrying in %.1fs...",
                    batch,
                    attempt,
                    max_retries,
                    exc,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            batch_close = _extract_close_frame(raw)
            if not batch_close.empty and batch_close.notna().any().any():
                if len(batch) == 1 and "single_ticker" in batch_close.columns:
                    batch_close = batch_close.rename(columns={"single_ticker": batch[0]})
                break

            wait_seconds = _retry_delay(attempt, base_sleep_seconds, jitter_seconds)
            logger.warning(
                "Batch %s returned empty data on attempt %s/%s. Retrying in %.1fs...",
                batch,
                attempt,
                max_retries,
                wait_seconds,
            )
            time.sleep(wait_seconds)

        if batch_close.empty or not batch_close.notna().any().any():
            failed_tickers.extend(batch)
            continue

        close_frames.append(batch_close)

    if not close_frames:
        return pd.DataFrame(), failed_tickers

    merged = pd.concat(close_frames, axis=1)
    merged = merged.loc[:, ~merged.columns.duplicated()]
    return merged, failed_tickers



def fetch_market_data(start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH, parse_dates=["Date"], index_col="Date")
        return df.dropna()

    tickers = _collect_all_tickers()

    batch_size = _env_int("MARKET_DL_BATCH_SIZE", default=4)
    max_retries = _env_int("MARKET_DL_MAX_RETRIES", default=4)
    base_sleep_seconds = _env_float("MARKET_DL_BASE_SLEEP_SECONDS", default=2.0)
    jitter_seconds = _env_float("MARKET_DL_JITTER_SECONDS", default=0.75)

    close, failed_tickers = _download_close_in_batches(
        tickers=tickers,
        start=start,
        end=end,
        batch_size=batch_size,
        max_retries=max_retries,
        base_sleep_seconds=base_sleep_seconds,
        jitter_seconds=jitter_seconds,
    )

    if close.empty:
        raise ValueError(
            "No market data downloaded. Yahoo may be rate-limiting. "
            "Batched retries were attempted; try again later or pre-populate data/market_data.csv."
        )

    if failed_tickers:
        logger.warning(
            "Ticker batches failed after retries: %s",
            ", ".join(failed_tickers),
        )

    market_data = _build_market_frame(close)

    if market_data.empty:
        raise ValueError("No valid market series were available from Yahoo Finance.")

    market_data = market_data.dropna(how="all")

    DATA_PATH.parent.mkdir(exist_ok=True)
    market_data.to_csv(DATA_PATH)

    return market_data