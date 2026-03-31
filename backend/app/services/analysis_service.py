import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import grangercausalitytests

SOURCE_LABELS = {
    "india": "India (Nifty 50)",
    "us": "US Market (S&P 500)",
    "fx": "USD/INR Exchange Rate",
    "global_vix": "Global Volatility Index",
}


def source_label(source: str | None) -> str | None:
    if source is None:
        return None
    return SOURCE_LABELS.get(source, source)

def prepare_analysis_data(prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices[["india", "us", "fx", "global_vix"]].pct_change().dropna()
    return returns

def run_var_analysis(prices: pd.DataFrame, maxlags: int = 5) -> dict:
    data = prepare_analysis_data(prices)

    model = VAR(data)
    results = model.fit(maxlags=maxlags, ic="aic")

    lag_order = results.k_ar

    # Find strongest lagged influence on India from non-India series
    strongest_driver = None
    strongest_value = 0.0

    for variable in ["us", "fx", "global_vix"]:
        for lag in range(1, lag_order + 1):
            coeff_name = f"L{lag}.{variable}"
            coeff_value = results.params.loc[coeff_name, "india"] if coeff_name in results.params.index else 0.0

            if abs(coeff_value) > abs(strongest_value):
                strongest_value = coeff_value
                strongest_driver = {
                    "source": source_label(variable),
                    "source_code": variable,
                    "lag_days": lag,
                    "coefficient": float(coeff_value),
                }

    summary = {
        "lag_order": int(lag_order),
        "strongest_driver": strongest_driver,
        "interpretation": (
            f"Strongest estimated lagged influence on India comes from "
            f"{strongest_driver['source']} after {strongest_driver['lag_days']} day(s)."
            if strongest_driver else "No strong lagged driver identified."
        )
    }
    return summary

def run_granger_analysis(prices: pd.DataFrame, maxlag: int = 5) -> dict:
    data = prepare_analysis_data(prices)

    candidates = ["us", "fx", "global_vix"]
    best_source = None
    best_pvalue = 1.0
    best_lag = None

    for source in candidates:
        # grangercausalitytests expects target first, source second in the dataframe
        test_data = data[["india", source]].dropna()
        results = grangercausalitytests(test_data, maxlag=maxlag, verbose=False)

        for lag in range(1, maxlag + 1):
            pvalue = results[lag][0]["ssr_ftest"][1]
            if pvalue < best_pvalue:
                best_pvalue = pvalue
                best_source = source
                best_lag = lag

    if best_source is not None:
        best_source_label = source_label(best_source)
        interpretation = (
            f"{best_source_label} is the most likely statistical source of contagion into India, "
            f"with strongest Granger evidence at lag {best_lag} (p={best_pvalue:.4f})."
        )
    else:
        best_source_label = None
        interpretation = "No statistically meaningful contagion source identified."

    return {
        "top_source": best_source_label,
        "top_source_code": best_source,
        "best_lag": best_lag,
        "p_value": float(best_pvalue),
        "interpretation": interpretation,
    }