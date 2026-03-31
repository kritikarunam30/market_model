from pathlib import Path
import os
import random
import time
import pandas as pd
import yfinance as yf


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"Invalid {name}={raw!r}; using default {default}.")
        return default
    return max(value, minimum)


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(f"Invalid {name}={raw!r}; using default {default}.")
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

def collect_all_tickers() -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()

    for market_signals in MARKET_CONFIG.values():
        for candidates in market_signals.values():
            for ticker in candidates:
                if ticker and ticker not in seen:
                    seen.add(ticker)
                    tickers.append(ticker)

    return tickers


def extract_close_frame(raw: pd.DataFrame) -> pd.DataFrame:
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

    if "Close" in raw.columns:
        return raw[["Close"]].rename(columns={"Close": "single_ticker"})
    if "Adj Close" in raw.columns:
        return raw[["Adj Close"]].rename(columns={"Adj Close": "single_ticker"})

    return pd.DataFrame(index=raw.index)


def build_market_frame(close: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    market_data = pd.DataFrame(index=close.index)
    missing_series: list[str] = []

    for market, signals in MARKET_CONFIG.items():
        for signal, candidates in signals.items():
            column_name = f"{market}_{signal}_close"
            selected = None

            for ticker in candidates:
                if ticker in close.columns and close[ticker].notna().any():
                    selected = ticker
                    break

            if selected is None:
                missing_series.append(column_name)
                continue

            market_data[column_name] = close[selected]

    return market_data, missing_series


def download_close_in_batches(
    tickers: list[str],
    start: str,
    end: str | None = None,
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
                print(
                    f"Batch {batch} failed on attempt {attempt}/{max_retries}: {exc}. "
                    f"Retrying in {wait_seconds:.1f}s..."
                )
                time.sleep(wait_seconds)
                continue

            batch_close = extract_close_frame(raw)

            if not batch_close.empty and batch_close.notna().any().any():
                if len(batch) == 1 and "single_ticker" in batch_close.columns:
                    batch_close = batch_close.rename(columns={"single_ticker": batch[0]})
                break

            wait_seconds = _retry_delay(attempt, base_sleep_seconds, jitter_seconds)
            print(
                f"Batch {batch} returned empty data on attempt {attempt}/{max_retries}. "
                f"Retrying in {wait_seconds:.1f}s..."
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

def main():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    data_file = data_dir / "market_data.csv"

    existing_data: pd.DataFrame | None = None
    start_date = "2018-01-01"
    today = pd.Timestamp.today().normalize()
    yesterday = today - pd.Timedelta(days=1)

    if data_file.exists():
        existing_data = pd.read_csv(data_file, parse_dates=["Date"], index_col="Date")
        existing_data.index = pd.to_datetime(existing_data.index, errors="coerce")
        existing_data = existing_data[~existing_data.index.isna()]

        if not existing_data.empty:
            last_date = existing_data.index.max().normalize()

            # Ensure we only download data between the last entry and yesterday
            if last_date >= yesterday:
                print("market_data.csv is already up to date; no new dates to download.")
                print(existing_data.tail())
                return

            start_date = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    end_date = yesterday.strftime("%Y-%m-%d")

    tickers = collect_all_tickers()

    batch_size = _env_int("MARKET_DL_BATCH_SIZE", default=4)
    max_retries = _env_int("MARKET_DL_MAX_RETRIES", default=4)
    base_sleep_seconds = _env_float("MARKET_DL_BASE_SLEEP_SECONDS", default=2.0)
    jitter_seconds = _env_float("MARKET_DL_JITTER_SECONDS", default=0.75)

    print(
        "Download tuning: "
        f"MARKET_DL_BATCH_SIZE={batch_size}, "
        f"MARKET_DL_MAX_RETRIES={max_retries}, "
        f"MARKET_DL_BASE_SLEEP_SECONDS={base_sleep_seconds}, "
        f"MARKET_DL_JITTER_SECONDS={jitter_seconds}"
    )

    close, failed_tickers = download_close_in_batches(
        tickers=tickers,
        start=start_date,
        end=end_date,
        batch_size=batch_size,
        max_retries=max_retries,
        base_sleep_seconds=base_sleep_seconds,
        jitter_seconds=jitter_seconds,
    )

    if close.empty:
        if existing_data is not None and not existing_data.empty:
            print("No new data returned for the requested incremental window.")
            print(existing_data.tail())
            return
        raise ValueError(
            "Download failed for all batches (likely rate limit). "
            "Try again later; batching/retries were already applied."
        )

    market_data, missing_series = build_market_frame(close)

    if market_data.empty:
        if existing_data is not None and not existing_data.empty:
            print("No valid new market series available; existing market_data.csv unchanged.")
            print(existing_data.tail())
            return
        raise ValueError("No valid market series available. Try again later.")

    market_data = market_data.dropna(how="all")

    if existing_data is not None and not existing_data.empty:
        market_data = pd.concat([existing_data, market_data], axis=0)
        market_data = market_data[~market_data.index.duplicated(keep="last")]
        market_data = market_data.sort_index()

    if failed_tickers:
        print("Ticker batches that failed after retries:")
        for ticker in failed_tickers:
            print(f"- {ticker}")

    if missing_series:
        print("Missing or unavailable series skipped:")
        for series in missing_series:
            print(f"- {series}")

    market_data.to_csv(data_file)
    print("Saved to data/market_data.csv")
    print(market_data.tail())

if __name__ == "__main__":
    main()