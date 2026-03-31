from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path

import pandas as pd
import yfinance as yf

from app.services.data_service import LEGACY_ALIAS_MAP, MARKET_CONFIG


DEFAULT_DATA_FILE = Path("data/market_data.csv")


def required_canonical_columns_strict() -> list[str]:
    columns: list[str] = []
    for market, signals in MARKET_CONFIG.items():
        for signal, candidates in signals.items():
            # Only require series that have at least one configured ticker candidate.
            if candidates:
                columns.append(f"{market}_{signal}_close")
    return columns


def required_runtime_columns() -> list[str]:
    # Runtime minimum used across risk/network/forecast flows.
    columns = [
        "india_equity_close",
        "india_vix_close",
        "india_fx_close",
        "india_commodity_close",
        "us_equity_close",
        "us_vix_close",
        "us_fx_close",
        "us_commodity_close",
        "uk_equity_close",
        "japan_equity_close",
        "china_equity_close",
        "germany_equity_close",
        "hong_kong_equity_close",
    ]
    return columns


def load_market_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError("CSV must contain a 'Date' column.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if df["Date"].isna().any():
        bad_rows = int(df["Date"].isna().sum())
        raise ValueError(f"Found {bad_rows} rows with invalid Date values.")

    return df


def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if col == "Date":
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _ensure_alias_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for alias, canonical in LEGACY_ALIAS_MAP.items():
        if alias not in out.columns and canonical in out.columns:
            out[alias] = out[canonical]
    return out


def _ensure_canonical_from_alias(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for alias, canonical in LEGACY_ALIAS_MAP.items():
        if canonical not in out.columns and alias in out.columns:
            out[canonical] = out[alias]
    return out


def _repair_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    value_columns = [col for col in out.columns if col != "Date"]

    # Interpolate by time to close interior gaps, then fill edge gaps.
    out = out.set_index("Date")
    out[value_columns] = out[value_columns].interpolate(method="time", limit_direction="both")
    out[value_columns] = out[value_columns].ffill().bfill()
    out = out.reset_index()

    return out


def _canonical_candidates_map() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for market, signals in MARKET_CONFIG.items():
        for signal, candidates in signals.items():
            canonical = f"{market}_{signal}_close"
            mapping[canonical] = [ticker for ticker in candidates if ticker]
    return mapping


def _download_close_series(
    candidates: list[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.Series | None, str | None]:
    # Try candidate tickers in order until one returns usable close data.
    for ticker in candidates:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            raw = yf.download(
                ticker,
                start=start.strftime("%Y-%m-%d"),
                end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        if raw.empty:
            continue

        if "Close" in raw.columns:
            series = raw["Close"]
        elif "Adj Close" in raw.columns:
            series = raw["Adj Close"]
        else:
            continue

        series = pd.to_numeric(series, errors="coerce").dropna()
        if series.empty:
            continue

        series.name = ticker
        series.index = pd.to_datetime(series.index, errors="coerce")
        series = series[~series.index.isna()]
        series = series[~series.index.duplicated(keep="last")]
        return series, ticker

    return None, None


def _repair_from_api(df: pd.DataFrame, required_columns: list[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    out = df.copy()
    out = out.set_index("Date")
    out.index = pd.to_datetime(out.index, errors="coerce")
    out = out[~out.index.isna()]
    out = out.sort_index()

    stats = {
        "columns_attempted": 0,
        "columns_filled": 0,
        "cells_filled": 0,
    }

    if out.empty:
        return out.reset_index(), stats

    candidates_by_column = _canonical_candidates_map()
    start = out.index.min()
    end = out.index.max()

    for col in required_columns:
        candidates = candidates_by_column.get(col, [])
        if not candidates:
            continue

        needs_repair = col not in out.columns or out[col].isna().any()
        if not needs_repair:
            continue

        stats["columns_attempted"] += 1
        downloaded, _ticker_used = _download_close_series(candidates, start, end)
        if downloaded is None:
            continue

        if col not in out.columns:
            out[col] = pd.NA

        before_missing = int(out[col].isna().sum())
        aligned = downloaded.reindex(out.index)
        out[col] = out[col].fillna(aligned)
        after_missing = int(out[col].isna().sum())

        filled_here = before_missing - after_missing
        if filled_here > 0:
            stats["columns_filled"] += 1
            stats["cells_filled"] += filled_here

    return out.reset_index(), stats


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop_duplicates(subset=["Date"], keep="last")
    out = out.sort_values("Date")

    value_columns = [col for col in out.columns if col != "Date"]
    if value_columns:
        out = out.dropna(subset=value_columns, how="all")

    out = out.reset_index(drop=True)
    return out


def validate(df: pd.DataFrame, required_columns: list[str]) -> list[str]:
    issues: list[str] = []

    if df.empty:
        issues.append("DataFrame is empty after processing.")
        return issues

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        issues.append(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    present_required = [col for col in required_columns if col in df.columns]
    missing_values = [col for col in present_required if df[col].isna().any()]
    if missing_values:
        issues.append(
            "Required columns still contain missing values: " + ", ".join(missing_values)
        )

    return issues


def process_file(path: Path, dry_run: bool, fail_on_issues: bool, strict_required: bool) -> int:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    required_columns = (
        required_canonical_columns_strict()
        if strict_required
        else required_runtime_columns()
    )
    original = load_market_csv(path)

    cleaned = original.copy()
    cleaned = _normalize_frame(cleaned)
    cleaned = _coerce_numeric_columns(cleaned)
    cleaned = _ensure_canonical_from_alias(cleaned)
    cleaned = _ensure_alias_columns(cleaned)
    cleaned, api_stats = _repair_from_api(cleaned, required_columns)
    cleaned = _repair_missing_values(cleaned)
    cleaned = _normalize_frame(cleaned)

    issues = validate(cleaned, required_columns)

    if not dry_run:
        cleaned.to_csv(path, index=False)

    total_missing_cells = int(cleaned.drop(columns=["Date"], errors="ignore").isna().sum().sum())
    required_missing_columns = [col for col in required_columns if col not in cleaned.columns]
    required_missing_value_columns = [
        col for col in required_columns if col in cleaned.columns and cleaned[col].isna().any()
    ]

    print("Final Data Report")
    print(f"- file: {path}")
    print(f"- rows: {len(cleaned)}")
    print(f"- columns: {len(cleaned.columns)}")
    print(f"- total_missing_cells: {total_missing_cells}")
    print(f"- api_columns_attempted: {api_stats['columns_attempted']}")
    print(f"- api_columns_filled: {api_stats['columns_filled']}")
    print(f"- api_cells_filled: {api_stats['cells_filled']}")
    if required_missing_columns:
        print("- missing_required_columns: " + ", ".join(required_missing_columns))
    else:
        print("- missing_required_columns: none")
    if required_missing_value_columns:
        print("- required_columns_with_missing_values: " + ", ".join(required_missing_value_columns))
    else:
        print("- required_columns_with_missing_values: none")
    print(f"- status: {'issues_found' if issues else 'ok'}")

    if issues and fail_on_issues:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and repair backend/data/market_data.csv so required market series "
            "columns exist and contain no missing values."
        )
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="Path to market CSV file (default: data/market_data.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation/repair checks but do not write changes.",
    )
    parser.add_argument(
        "--no-fail-on-issues",
        action="store_true",
        help="Exit with code 0 even if validation issues remain.",
    )
    parser.add_argument(
        "--strict-required",
        action="store_true",
        help=(
            "Require all configured canonical series from MARKET_CONFIG. "
            "By default only runtime-critical columns are required."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return process_file(
        path=args.file,
        dry_run=args.dry_run,
        fail_on_issues=not args.no_fail_on_issues,
        strict_required=args.strict_required,
    )


if __name__ == "__main__":
    raise SystemExit(main())
