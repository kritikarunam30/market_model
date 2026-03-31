import pandas as pd

def _pick_column(prices: pd.DataFrame, candidates: list[str]) -> str | None:
    for name in candidates:
        if name in prices.columns and prices[name].notna().any():
            return name
    return None


def build_network(prices: pd.DataFrame, threshold: float = 0.0) -> dict:
    india_col = _pick_column(prices, ["india_equity_close", "india"])
    if india_col is None:
        return {"nodes": [], "edges": []}

    market_columns = {
        "us": _pick_column(prices, ["us_equity_close", "us"]),
        "uk": _pick_column(prices, ["uk_equity_close"]),
        "japan": _pick_column(prices, ["japan_equity_close"]),
        "germany": _pick_column(prices, ["germany_equity_close"]),
        "hong_kong": _pick_column(prices, ["hong_kong_equity_close"]),
        "china": _pick_column(prices, ["china_equity_close"]),
    }

    nodes = [{"id": "india", "label": "INDIA"}]
    edges = []

    india_returns = prices[india_col].pct_change()

    for market, market_col in market_columns.items():
        if market_col is None:
            continue

        pair = pd.concat([india_returns, prices[market_col].pct_change()], axis=1).dropna()
        if len(pair) < 20:
            continue

        corr_value = pair.iloc[:, 0].corr(pair.iloc[:, 1])
        if pd.isna(corr_value):
            continue

        nodes.append({"id": market, "label": market.upper()})

        if abs(float(corr_value)) >= threshold:
            edges.append(
                {
                    "source": "india",
                    "target": market,
                    "weight": round(float(corr_value), 3),
                }
            )

    return {"nodes": nodes, "edges": edges}