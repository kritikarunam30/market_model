import pandas as pd
import numpy as np

GLOBAL_MARKETS = ["us", "uk", "japan", "germany", "hong_kong", "china"]

SIGNAL_WEIGHTS = {
    "equity_vol_score": 0.35,
    "vix_level_score": 0.25,
    "fx_vol_score": 0.15,
    "bond_vol_score": 0.15,
    "commodity_vol_score": 0.10,
}

RISK_COMPONENT_WEIGHTS = {
    "india_domestic_score": 0.30,
    "global_market_score": 0.30,
    "india_global_corr_score": 0.15,
    "india_drawdown_score": 0.15,
    "global_vix_score": 0.10,
}

def minmax_series(series: pd.Series) -> pd.Series:
    s = series.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty or s.max() == s.min():
        return pd.Series(index=series.index, data=50.0)
    scaled = (series - s.min()) / (s.max() - s.min())
    return (scaled * 100).clip(0, 100)


def _rolling_vol_score(series: pd.Series, window: int = 20) -> pd.Series:
    returns = series.pct_change()
    vol = returns.rolling(window).std()
    return minmax_series(vol)


def _weighted_average(score_map: dict[str, pd.Series], weight_map: dict[str, float]) -> pd.Series:
    if not score_map:
        return pd.Series(dtype=float)

    frame = pd.concat(score_map, axis=1)
    value_sum = pd.Series(0.0, index=frame.index)
    weight_sum = pd.Series(0.0, index=frame.index)

    for name, series in score_map.items():
        weight = weight_map.get(name, 0.0)
        valid = series.notna()
        value_sum.loc[valid] += series.loc[valid] * weight
        weight_sum.loc[valid] += weight

    weighted = value_sum / weight_sum.replace(0.0, np.nan)
    return weighted


def _market_signal_scores(prices: pd.DataFrame, market: str) -> dict[str, pd.Series]:
    score_map: dict[str, pd.Series] = {}

    equity_col = f"{market}_equity_close"
    vix_col = f"{market}_vix_close"
    fx_col = f"{market}_fx_close"
    bond_col = f"{market}_bond_close"
    commodity_col = f"{market}_commodity_close"

    if equity_col in prices.columns:
        score_map["equity_vol_score"] = _rolling_vol_score(prices[equity_col])
    if vix_col in prices.columns:
        score_map["vix_level_score"] = minmax_series(prices[vix_col])
    if fx_col in prices.columns:
        score_map["fx_vol_score"] = _rolling_vol_score(prices[fx_col])
    if bond_col in prices.columns:
        score_map["bond_vol_score"] = _rolling_vol_score(prices[bond_col])
    if commodity_col in prices.columns:
        score_map["commodity_vol_score"] = _rolling_vol_score(prices[commodity_col])

    return score_map

def compute_drawdown(price_series: pd.Series) -> pd.Series:
    running_max = price_series.cummax()
    drawdown = (price_series - running_max) / running_max
    return drawdown

def compute_risk_index(prices: pd.DataFrame) -> pd.DataFrame:
    prices = prices.copy().sort_index()
    prices = prices.replace([np.inf, -np.inf], np.nan)
    prices = prices.ffill()

    # India domestic macro-financial stress (equity, VIX, FX, rates, commodities).
    india_signals = _market_signal_scores(prices, "india")
    india_domestic_score = _weighted_average(india_signals, SIGNAL_WEIGHTS)

    # Global market stress from each external market using the same signal set.
    external_market_scores: list[pd.Series] = []
    external_score_columns: dict[str, pd.Series] = {}
    for market in GLOBAL_MARKETS:
        market_signals = _market_signal_scores(prices, market)
        market_score = _weighted_average(market_signals, SIGNAL_WEIGHTS)
        if market_score.empty:
            continue
        external_market_scores.append(market_score)
        external_score_columns[f"{market}_macro_score"] = market_score

    if external_market_scores:
        global_market_frame = pd.concat(external_market_scores, axis=1)
        global_market_score = global_market_frame.mean(axis=1, skipna=True)
    else:
        global_market_score = pd.Series(index=prices.index, dtype=float)

    # Dedicated global VIX signal retained as an additional systemic factor.
    if "global_vix" in prices.columns:
        global_vix_score = minmax_series(prices["global_vix"])
    elif "us_vix_close" in prices.columns:
        global_vix_score = minmax_series(prices["us_vix_close"])
    else:
        global_vix_score = pd.Series(index=prices.index, dtype=float)

    india_equity_col = "india_equity_close" if "india_equity_close" in prices.columns else "india"
    india_equity_returns = prices[india_equity_col].pct_change() if india_equity_col in prices.columns else pd.Series(index=prices.index, dtype=float)

    global_equity_cols = [f"{market}_equity_close" for market in GLOBAL_MARKETS if f"{market}_equity_close" in prices.columns]
    if global_equity_cols:
        global_equity_returns = prices[global_equity_cols].pct_change().mean(axis=1, skipna=True)
        india_global_corr = india_equity_returns.rolling(20).corr(global_equity_returns)
        india_global_corr_score = minmax_series(india_global_corr.abs())
    else:
        india_global_corr_score = pd.Series(index=prices.index, dtype=float)

    if india_equity_col in prices.columns:
        india_drawdown_score = minmax_series(compute_drawdown(prices[india_equity_col]).abs())
    else:
        india_drawdown_score = pd.Series(index=prices.index, dtype=float)

    aligned = pd.concat(
        [
            india_domestic_score.rename("india_domestic_score"),
            global_market_score.rename("global_market_score"),
            india_global_corr_score.rename("india_global_corr_score"),
            india_drawdown_score.rename("india_drawdown_score"),
            global_vix_score.rename("global_vix_score"),
            pd.DataFrame(external_score_columns),
        ],
        axis=1,
    )

    component_scores = {
        "india_domestic_score": aligned["india_domestic_score"],
        "global_market_score": aligned["global_market_score"],
        "india_global_corr_score": aligned["india_global_corr_score"],
        "india_drawdown_score": aligned["india_drawdown_score"],
        "global_vix_score": aligned["global_vix_score"],
    }
    aligned["risk_index"] = _weighted_average(component_scores, RISK_COMPONENT_WEIGHTS).clip(0, 100)

    aligned = aligned.dropna(subset=["risk_index"]).copy()
    aligned["risk_label"] = pd.cut(
        aligned["risk_index"],
        bins=[-0.1, 33, 66, 100],
        labels=["Low", "Medium", "High"],
    )

    # Legacy aliases kept for downstream compatibility.
    aligned["india_vol_score"] = aligned["india_domestic_score"]
    aligned["fx_vol_score"] = aligned["global_market_score"]
    aligned["corr_score"] = aligned["india_global_corr_score"]
    aligned["drawdown_score"] = aligned["india_drawdown_score"]
    aligned["vix_score"] = aligned["global_vix_score"]

    result = aligned.reset_index()

    if "Date" in result.columns:
        result = result.rename(columns={"Date": "date"})
    elif "index" in result.columns:
        result = result.rename(columns={"index": "date"})

    return result
