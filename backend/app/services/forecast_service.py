import pandas as pd
from xgboost import XGBRegressor, DMatrix
from sklearn.model_selection import train_test_split
from app.services.risk_service import compute_risk_index


SIGNAL_SUFFIXES = ("equity_close", "vix_close", "fx_close", "bond_close", "commodity_close")

LEGACY_TO_CANONICAL = {
    "india": "india_equity_close",
    "us": "us_equity_close",
    "india_vix": "india_vix_close",
    "global_vix": "us_vix_close",
    "fx": "india_fx_close",
}


def _detect_markets(prices: pd.DataFrame) -> list[str]:
    markets: set[str] = set()
    for col in prices.columns:
        for suffix in SIGNAL_SUFFIXES:
            token = f"_{suffix}"
            if col.endswith(token):
                markets.add(col[: -len(token)])
                break

    ordered = sorted(markets)
    if "india" in ordered:
        ordered.remove("india")
        ordered.insert(0, "india")
    return ordered


def _select_stress_proxy(features: pd.DataFrame, market: str) -> pd.Series | None:
    candidates = [
        f"{market}_vix_change",
        f"{market}_equity_vol_rolling_20",
        f"{market}_drawdown",
    ]
    for col in candidates:
        if col in features.columns:
            return features[col]
    return None


def _print_forecast_summary(
    model_name: str,
    data_last_updated: str,
    training_window: str,
    markets_used: list[str],
    lag_selected: str,
    forecast_horizon: str,
    confidence_note: str,
    top_features: list[tuple[str, float]] | None = None,
    feature_importance: list[tuple[str, float]] | None = None,
    shap_values: list[tuple[str, float]] | None = None,
) -> None:
    print("\n" + "=" * 72)
    print("FORECAST RUN SUMMARY")
    print("=" * 72)
    print(f"model name: {model_name}")
    print(f"data last updated: {data_last_updated}")
    print(f"training window: {training_window}")
    print(f"markets used: {', '.join(markets_used)}")
    print(f"lag selected: {lag_selected}")
    print(f"forecast horizon: {forecast_horizon}")
    print(f"confidence note/disclaimer: {confidence_note}")

    if top_features:
        print("\ntop features affecting forecast:")
        for name, value in top_features:
            print(f"- {name}: {value:.6f}")

    if feature_importance:
        print("\nfeature importance (xgboost gain proxy):")
        for name, value in feature_importance:
            print(f"- {name}: {value:.6f}")

    if shap_values:
        print("\nSHAP-like values (XGBoost pred_contribs for latest forecast):")
        for name, value in shap_values:
            print(f"- {name}: {value:.6f}")

    print("=" * 72 + "\n")

def build_forecast_features(prices: pd.DataFrame) -> pd.DataFrame:
    prices = prices.copy()
    for legacy_col, canonical_col in LEGACY_TO_CANONICAL.items():
        if legacy_col in prices.columns and canonical_col not in prices.columns:
            prices[canonical_col] = prices[legacy_col]

    risk_df = compute_risk_index(prices).copy()
    risk_df["date"] = pd.to_datetime(risk_df["date"])
    risk_df = risk_df.set_index("date")

    features = risk_df.copy()

    # Keep legacy feature names for downstream compatibility.
    legacy_return_map = {
        "india": "india_ret",
        "fx": "fx_ret",
        "us": "us_ret",
        "global_vix": "global_vix_ret",
    }
    for source_col, feature_col in legacy_return_map.items():
        if source_col in prices.columns:
            features[feature_col] = prices[source_col].pct_change()

    markets = _detect_markets(prices)
    for market in markets:
        equity_col = f"{market}_equity_close"
        vix_col = f"{market}_vix_close"
        fx_col = f"{market}_fx_close"
        bond_col = f"{market}_bond_close"
        commodity_col = f"{market}_commodity_close"

        if equity_col in prices.columns:
            equity_return = prices[equity_col].pct_change()
            features[f"{market}_equity_return"] = equity_return
            features[f"{market}_equity_vol_rolling_5"] = equity_return.rolling(5).std()
            features[f"{market}_equity_vol_rolling_20"] = equity_return.rolling(20).std()

            running_max = prices[equity_col].cummax()
            features[f"{market}_drawdown"] = (prices[equity_col] - running_max) / running_max

        if vix_col in prices.columns:
            features[f"{market}_vix_change"] = prices[vix_col].pct_change()

        if fx_col in prices.columns:
            features[f"{market}_fx_return"] = prices[fx_col].pct_change()

        if bond_col in prices.columns:
            features[f"{market}_bond_change"] = prices[bond_col].diff()

        if commodity_col in prices.columns:
            features[f"{market}_commodity_return"] = prices[commodity_col].pct_change()

    india_equity = features.get("india_equity_return")
    india_stress = _select_stress_proxy(features, "india")
    if india_equity is not None:
        for market in markets:
            if market == "india":
                continue

            market_equity_col = f"{market}_equity_return"
            if market_equity_col in features.columns:
                corr_20 = features[market_equity_col].rolling(20).corr(india_equity)
                features[f"{market}_india_corr_20"] = corr_20
                features[f"{market}_india_corr_20_lag_1"] = corr_20.shift(1)
                features[f"{market}_india_equity_lag_1"] = features[market_equity_col].shift(1)

            market_stress = _select_stress_proxy(features, market)
            if india_stress is not None and market_stress is not None:
                stress_corr_20 = market_stress.rolling(20).corr(india_stress)
                features[f"{market}_india_stress_corr_20"] = stress_corr_20
                features[f"{market}_india_stress_corr_20_lag_1"] = stress_corr_20.shift(1)

    features["risk_lag_1"] = features["risk_index"].shift(1)
    features["risk_lag_2"] = features["risk_index"].shift(2)
    features["risk_lag_3"] = features["risk_index"].shift(3)

    for base_col in ["india_ret", "us_ret", "fx_ret", "global_vix_ret"]:
        if base_col in features.columns:
            features[f"{base_col}_lag_1"] = features[base_col].shift(1)

    features["risk_ma_3"] = features["risk_index"].rolling(3).mean()
    features["risk_ma_5"] = features["risk_index"].rolling(5).mean()

    # target = next day's risk
    features["target_next_day_risk"] = features["risk_index"].shift(-1)

    features = features.dropna(axis=1, how="all")
    features = features.dropna()
    return features

def run_xgboost_forecast(prices: pd.DataFrame) -> dict:
    df = build_forecast_features(prices)
    latest_date_str = prices.index.max().strftime("%Y-%m-%d")
    training_window = f"{df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}"
    markets_used = _detect_markets(prices)
    lag_selected = "risk lags: 1,2,3 | market return lags: 1"
    forecast_horizon = "1 trading day ahead"
    confidence_note = (
        "Model output is probabilistic and data-dependent. Use as decision support, "
        "not as financial advice."
    )

    base_feature_cols = [
        "risk_lag_1", "risk_lag_2", "risk_lag_3",
        "india_ret_lag_1", "us_ret_lag_1", "fx_ret_lag_1", "global_vix_ret_lag_1",
        "risk_ma_3", "risk_ma_5"
    ]
    feature_cols = [col for col in base_feature_cols if col in df.columns]

    dynamic_feature_cols = [
        col for col in df.columns
        if col not in {"target_next_day_risk", "risk_index", *feature_cols}
    ]

    numeric_dynamic_feature_cols = [
        col for col in dynamic_feature_cols
        if pd.api.types.is_numeric_dtype(df[col])
    ]
    feature_cols.extend(sorted(numeric_dynamic_feature_cols))

    if not feature_cols:
        last_value = float(df["risk_index"].iloc[-1])
        _print_forecast_summary(
            model_name="fallback_last_value",
            data_last_updated=latest_date_str,
            training_window=training_window,
            markets_used=markets_used,
            lag_selected=lag_selected,
            forecast_horizon=forecast_horizon,
            confidence_note=confidence_note,
        )
        return {
            "forecast_next_day_risk": last_value,
            "method": "fallback_last_value",
            "model_error_mae": None,
        }

    X = df[feature_cols]
    y = df["target_next_day_risk"]

    if len(df) < 50:
        last_value = float(df["risk_index"].iloc[-1])
        _print_forecast_summary(
            model_name="fallback_last_value",
            data_last_updated=latest_date_str,
            training_window=training_window,
            markets_used=markets_used,
            lag_selected=lag_selected,
            forecast_horizon=forecast_horizon,
            confidence_note=confidence_note,
        )
        return {
            "forecast_next_day_risk": last_value,
            "method": "fallback_last_value",
            "model_error_mae": None,
        }

    X_train, _, y_train, _ = train_test_split(
        X, y, shuffle=False, test_size=0.2
    )

    model = XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        objective="reg:squarederror",
        random_state=42
    )
    model.fit(X_train, y_train)

    latest_features = X.iloc[[-1]]
    next_day_forecast = float(model.predict(latest_features)[0])

    sorted_feature_importance = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )

    # pred_contribs provides SHAP-like feature contributions from the trained booster.
    dmatrix_latest = DMatrix(latest_features, feature_names=feature_cols)
    contribs = model.get_booster().predict(dmatrix_latest, pred_contribs=True)[0]
    shap_like_pairs = list(zip(feature_cols, contribs[:-1]))
    top_features = sorted(
        shap_like_pairs,
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:5]

    _print_forecast_summary(
        model_name="xgboost_regressor",
        data_last_updated=latest_date_str,
        training_window=training_window,
        markets_used=markets_used,
        lag_selected=lag_selected,
        forecast_horizon=forecast_horizon,
        confidence_note=confidence_note,
        top_features=[(name, float(value)) for name, value in top_features],
        feature_importance=[(name, float(value)) for name, value in sorted_feature_importance],
        shap_values=[(name, float(value)) for name, value in shap_like_pairs],
    )
    return {
        "data_last_updated": latest_date_str,
        "forecast_next_day_risk": round(next_day_forecast, 2),
        "method": "xgboost_regressor",
        "feature_importance": {
            col: float(score)
            for col, score in zip(feature_cols, model.feature_importances_)
        },
        "confidence_note": confidence_note,
        "top_features_affecting_forecast": {
            col: float(score)
            for col, score in top_features
        },
        "shap_values": {
            col: float(score)
            for col, score in shap_like_pairs
        },
    }