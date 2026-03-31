import { useEffect, useMemo, useState } from "react";
import ContagionNetwork from "../components/ContagionNetwork";
import MetricCard from "../components/MetricCard";
import PlotlyChart from "../components/PlotlyChart";
import {
  fetchRiskIndex,
  fetchVarAnalysis,
  fetchGrangerAnalysis,
  fetchForecast,
  fetchNetwork,
} from "../api/marketApi";

const BREAKDOWN_ITEMS = [
  {
    key: "india_domestic_contribution",
    label: "India Domestic Macro Contribution",
  },
  {
    key: "global_market_contribution",
    label: "Global Markets Macro Contribution",
  },
  {
    key: "global_vix_contribution",
    label: "Global Volatility Index Contribution (VIX)",
  },
  {
    key: "india_drawdown_contribution",
    label: "India Drawdown Contribution",
  },
  {
    key: "india_global_correlation_contribution",
    label: "India-Global Correlation Contribution",
  },
];

export default function Dashboard() {
  const [selectedCountry, setSelectedCountry] = useState("india");
  const [risk, setRisk] = useState(null);
  const [varData, setVarData] = useState(null);
  const [grangerData, setGrangerData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const riskBreakdown = risk?.current?.breakdown;
  const marketMacroScores = risk?.current?.market_macro_scores || {};

  const countryOptions = useMemo(
    () =>
      Object.entries(marketMacroScores).map(([code, details]) => ({
        code,
        label: details?.label || code,
      })),
    [marketMacroScores]
  );

  const selectedCountryDetails = useMemo(
    () =>
      marketMacroScores[selectedCountry]
      || (countryOptions.length ? marketMacroScores[countryOptions[0].code] : null),
    [marketMacroScores, selectedCountry, countryOptions]
  );

  const metricCards = [
    {
      title: "Systemic Risk Score",
      value: risk?.current?.risk_index ?? "N/A",
      subtitle: `Current systemic risk level (${risk?.current?.risk_label ?? "N/A"})`,
    },
    {
      title: "Contagion Timing",
      value:
        varData?.strongest_driver?.lag_days != null
          ? `${varData.strongest_driver.lag_days} day(s)`
          : "N/A",
      subtitle: varData?.interpretation ?? "Estimated transmission lag",
    },
    {
      title: "Contagion Source",
      value: grangerData?.top_source ?? "N/A",
      subtitle: grangerData?.interpretation ?? "Top probable source market",
    },
    {
      title: "Next-Day Risk Forecast",
      value: forecastData?.forecast_next_day_risk ?? "N/A",
      subtitle: forecastData?.method ?? "Predicted risk level",
    },
  ];

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [riskData, varRes, grangerRes, forecastRes, networkData] =
          await Promise.all([
            fetchRiskIndex(),
            fetchVarAnalysis(),
            fetchGrangerAnalysis(),
            fetchForecast(),
            fetchNetwork(),
          ]);

        setRisk(riskData);
        setVarData(varRes);
        setGrangerData(grangerRes);
        setForecastData(forecastRes);
        setNetwork(networkData);
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const availableCodes = Object.keys(marketMacroScores);
    if (!availableCodes.length) return;
    if (!marketMacroScores[selectedCountry]) {
      setSelectedCountry(availableCodes[0]);
    }
  }, [marketMacroScores, selectedCountry]);

  if (loading) {
    return (
      <div className="min-h-screen px-4 py-20">
        <div className="max-w-6xl mx-auto text-center text-gray-300">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen px-4 py-20">
        <div className="max-w-6xl mx-auto text-center text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <section className="relative overflow-hidden py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="absolute top-20 left-10 w-32 h-32 bg-neon-green/10 rounded-full blur-3xl animate-float"></div>
          <div className="absolute bottom-24 right-12 w-40 h-40 bg-neon-blue/10 rounded-full blur-3xl animate-float" style={{ animationDelay: "2s" }}></div>

          <div className="relative z-10">
            <h1 className="text-4xl md:text-5xl font-bold mb-4 text-center">
              <span className="text-neon-green">
                Market Contagion Dashboard
              </span>
            </h1>
            <p className="text-center text-gray-300 max-w-3xl mx-auto mb-12">
              Monitor cross-market spillovers, forecast risk levels, and inspect network contagion using the latest available data.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {metricCards.map((card) => (
                <MetricCard
                  key={card.title}
                  title={card.title}
                  value={card.value}
                  subtitle={card.subtitle}
                />
              ))}
            </div>

            <div className="glass rounded-2xl p-4 md:p-6 mt-8 mb-8">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <h2 className="text-2xl font-bold text-white">Country Macro Stress Score</h2>
                <div className="w-full md:w-64">
                  <label className="text-xs uppercase tracking-wide text-gray-400 mb-1 block">
                    Select Country
                  </label>
                  <select
                    value={selectedCountry}
                    onChange={(e) => setSelectedCountry(e.target.value)}
                    className="w-full rounded-lg border border-neon-green/30 bg-black/40 px-3 py-2 text-white transition-colors duration-300 hover:border-neon-green/60 hover:bg-black/50 focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  >
                    {countryOptions.map((option) => (
                      <option key={option.code} value={option.code} className="bg-black text-white">
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="mt-5 rounded-xl border border-neon-green/20 bg-black/20 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-neon-green/40 hover:bg-black/30 hover:shadow-neon">
                <p className="text-sm text-gray-400">
                  {selectedCountryDetails?.label || "Selected Country"} macro stress score
                </p>
                <p className="text-4xl font-bold text-neon-green mt-1">
                  {selectedCountryDetails?.score != null ? selectedCountryDetails.score : "N/A"}
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  Score normalized to 0-100 using market equity, VIX, FX, rates, and commodity indicators.
                </p>
              </div>
            </div>
            <br />           

            <div className="glass rounded-2xl p-4 md:p-6 mb-8">
              <h2 className="text-3xl font-bold mb-8 text-center text-white">
                Breakdown of Risk Score
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {BREAKDOWN_ITEMS.map((item) => (
                  <div key={item.key} className="rounded-xl border border-neon-green/20 bg-black/20 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-neon-green/40 hover:bg-black/30 hover:shadow-neon">
                    <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">{item.label}</p>
                    <p className="text-2xl font-semibold text-neon-green">
                      {riskBreakdown?.[item.key] != null ? `${riskBreakdown[item.key]}%` : "N/A"}
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-400 mt-4">
                Contributions are percentage shares of the current composite risk score.
              </p>         
            </div>
            <br />
              <p className="text-center text-gray-300 max-w-3xl mx-auto mb-12">
                Last Market Date: {forecastData?.data_last_updated ? `${forecastData.data_last_updated}` : "N/A"} (based on latest Yahoo Finance data)
              </p>
          </div>
        </div>
      </section>

      <section className="py-20 px-4 border-t border-neon-green/10">
        <div className="max-w-6xl mx-auto">      
          <h2 className="text-3xl font-bold mb-8 text-center text-white">
            Time Series Visualization
          </h2>
          <PlotlyChart
            history={risk?.history}
            loading={loading}
            error={error}
          />
        </div>
      </section>

      <section className="py-20 px-4 border-t border-neon-green/10">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center text-white">
            India-Centric Global Influence Map
          </h2>
          <div className="glass rounded-2xl p-4 md:p-6">
            <ContagionNetwork data={network} macroScores={marketMacroScores} />
          </div>
        </div>
      </section>
    </div>
  );
}