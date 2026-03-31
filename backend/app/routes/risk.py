from fastapi import APIRouter
import numpy as np
from app.services.data_service import fetch_market_data
from app.services.risk_service import compute_risk_index

router = APIRouter()

MARKET_LABELS = {
    "india": "India",
    "us": "United States",
    "uk": "United Kingdom",
    "japan": "Japan",
    "germany": "Germany",
    "hong_kong": "Hong Kong",
    "china": "China",
}

MARKET_SCORE_COLUMN_MAP = {
    "india": "india_domestic_score",
    "us": "us_macro_score",
    "uk": "uk_macro_score",
    "japan": "japan_macro_score",
    "germany": "germany_macro_score",
    "hong_kong": "hong_kong_macro_score",
    "china": "china_macro_score",
}

RISK_WEIGHTS = {
    "india_domestic": 0.30,
    "global_markets": 0.30,
    "global_vix": 0.10,
    "india_drawdown": 0.15,
    "india_global_correlation": 0.15,
}

_COMPONENT_FIELDS = [
    ("india_domestic", "india_domestic_score", "india_domestic"),
    ("global_market", "global_market_score", "global_markets"),
    ("global_vix", "global_vix_score", "global_vix"),
    ("india_drawdown", "india_drawdown_score", "india_drawdown"),
    ("india_global_correlation", "india_global_corr_score", "india_global_correlation"),
]


def _build_market_macro_scores(row) -> dict:
    market_scores = {}

    for market, column in MARKET_SCORE_COLUMN_MAP.items():
        if column not in row.index:
            continue

        value = row[column]
        if value is None:
            continue

        try:
            if np.isnan(value):
                continue
        except TypeError:
            pass

        market_scores[market] = {
            "label": MARKET_LABELS.get(market, market.replace("_", " ").title()),
            "score": round(float(value), 2),
        }

    return market_scores


def _build_breakdown(row) -> dict:
    scores = {
        name: float(row[score_col])
        for name, score_col, _ in _COMPONENT_FIELDS
    }
    values = {
        name: scores[name] * RISK_WEIGHTS[weight_key]
        for name, _, weight_key in _COMPONENT_FIELDS
    }
    total_value = sum(values.values())

    if total_value > 0:
        percents = {
            name: (value / total_value) * 100
            for name, value in values.items()
        }
    else:
        percents = {name: 0.0 for name in values}

    breakdown = {}
    for name, score_col, _ in _COMPONENT_FIELDS:
        breakdown[f"{name}_contribution"] = round(percents[name], 2)
        breakdown[f"{name}_contribution_value"] = round(values[name], 2)
        score_alias = "india_global_correlation_score" if name == "india_global_correlation" else score_col
        breakdown[score_alias] = round(scores[name], 2)

    # Legacy aliases for existing UI clients.
    breakdown["india_volatility_contribution"] = breakdown["india_domestic_contribution"]
    breakdown["fx_contribution"] = breakdown["global_market_contribution"]
    breakdown["vix_contribution"] = breakdown["global_vix_contribution"]
    breakdown["drawdown_contribution"] = breakdown["india_drawdown_contribution"]
    breakdown["correlation_contribution"] = breakdown["india_global_correlation_contribution"]

    return breakdown

@router.get("/risk-index")
def get_risk_index():
    prices = fetch_market_data()
    risk_df = compute_risk_index(prices)

    if risk_df.empty:
        return {
            "current": None,
            "history": [],
            "detail": "Not enough data to compute systemic risk index.",
        }

    latest_row = risk_df.iloc[-1]

    current = {
        "date": latest_row["date"],
        "risk_index": round(float(latest_row["risk_index"]), 2),
        "risk_label": str(latest_row["risk_label"]),
        "breakdown": _build_breakdown(latest_row),
        "market_macro_scores": _build_market_macro_scores(latest_row),
    }

    base_history_columns = {
        "date",
        "risk_index",
        "risk_label",
        "india_domestic_score",
        "global_market_score",
        "global_vix_score",
        "india_drawdown_score",
        "india_global_corr_score",
    }
    market_score_columns = [
        column
        for column in MARKET_SCORE_COLUMN_MAP.values()
        if column in risk_df.columns and column not in base_history_columns
    ]

    history = risk_df[
        [
            "date",
            "risk_index",
            "risk_label",
            "india_domestic_score",
            "global_market_score",
            "global_vix_score",
            "india_drawdown_score",
            "india_global_corr_score",
            *market_score_columns,
        ]
    ].tail(120).copy()

    for name, score_col, weight_key in _COMPONENT_FIELDS:
        history[f"{name}_contribution_value"] = history[score_col] * RISK_WEIGHTS[weight_key]

    history_total = (
        history["india_domestic_contribution_value"]
        + history["global_market_contribution_value"]
        + history["global_vix_contribution_value"]
        + history["india_drawdown_contribution_value"]
        + history["india_global_correlation_contribution_value"]
    )
    history_total = history_total.replace(0, np.nan)

    for name, _, _ in _COMPONENT_FIELDS:
        history[f"{name}_contribution"] = (
            history[f"{name}_contribution_value"] / history_total * 100
        ).fillna(0)

    history_round_cols = [
        "risk_index",
        "india_domestic_score",
        "global_market_score",
        "global_vix_score",
        "india_drawdown_score",
        "india_global_corr_score",
    ]
    for name, _, _ in _COMPONENT_FIELDS:
        history_round_cols.extend([
            f"{name}_contribution",
            f"{name}_contribution_value",
        ])
    for col in history_round_cols:
        history[col] = history[col].round(2)

    # Legacy aliases for existing UI clients.
    history["india_volatility_contribution"] = history["india_domestic_contribution"]
    history["fx_contribution"] = history["global_market_contribution"]
    history["vix_contribution"] = history["global_vix_contribution"]
    history["drawdown_contribution"] = history["india_drawdown_contribution"]
    history["correlation_contribution"] = history["india_global_correlation_contribution"]
    history["india_vol_score"] = history["india_domestic_score"]
    history["fx_vol_score"] = history["global_market_score"]
    history["vix_score"] = history["global_vix_score"]
    history["drawdown_score"] = history["india_drawdown_score"]
    history["corr_score"] = history["india_global_corr_score"]
    history["market_macro_scores"] = history.apply(_build_market_macro_scores, axis=1)

    return {
        "current": current,
        "history": history.to_dict(orient="records"),
    }