import { Suspense, useMemo } from "react";
import PlotModule from "react-plotly.js";

const Plot = PlotModule?.default?.default ?? PlotModule?.default ?? PlotModule;

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const toNumberOrNull = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatNumeric = (value, decimals = 3) => {
  const parsed = toNumberOrNull(value);
  return parsed == null ? "N/A" : parsed.toFixed(decimals);
};

const formatLabel = (value) => {
  if (typeof value !== "string" || !value.trim()) return "Unknown";
  return value
    .replace(/_/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const MARKET_TO_ISO3 = {
  us: "USA",
  usa: "USA",
  united_states: "USA",
  us_market: "USA",
  us_market_sp_500: "USA",
  sp_500: "USA",
  s_p_500: "USA",
  dxy: "USA",
  usd_index: "USA",
  us_dollar_index: "USA",
  global_vix: "USA",
  global_volatility_index: "USA",
  vix: "USA",
  fx: "USA",
  usd_inr_exchange_rate: "USA",
  uk: "GBR",
  gb: "GBR",
  united_kingdom: "GBR",
  britain: "GBR",
  japan: "JPN",
  jp: "JPN",
  china: "CHN",
  cn: "CHN",
  germany: "DEU",
  de: "DEU",
  hong_kong: "HKG",
  hongkong: "HKG",
  hk: "HKG",
  france: "FRA",
  fr: "FRA",
  singapore: "SGP",
  sg: "SGP",
  australia: "AUS",
  au: "AUS",
  canada: "CAN",
  ca: "CAN",
};

const normalizeMarketKey = (value) => {
  if (value == null) return "";

  return String(value)
    .toLowerCase()
    .replace(/\([^)]*\)/g, " ")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
};

const resolveIso3 = (row) => {
  const market = normalizeMarketKey(row?.market);
  const country = normalizeMarketKey(row?.country);

  if (/^[a-z]{3}$/.test(market)) return market.toUpperCase();
  if (/^[a-z]{3}$/.test(country)) return country.toUpperCase();

  return MARKET_TO_ISO3[market] || MARKET_TO_ISO3[country] || null;
};

const resolveMacroScore = (market, macroScores) => {
  if (!macroScores || typeof macroScores !== "object") return null;

  const key = normalizeMarketKey(market);
  if (!key) return null;

  const aliases = [
    key,
    key.replace(/_market$/, ""),
    key.replace(/_equity$/, ""),
    key.replace(/_equity_close$/, ""),
  ];

  for (const alias of aliases) {
    const direct = macroScores[alias]?.score;
    const parsedDirect = toNumberOrNull(direct);
    if (parsedDirect != null) return parsedDirect;
  }

  const matchedKey = Object.keys(macroScores).find((candidate) => normalizeMarketKey(candidate) === key);
  const parsedMatched = toNumberOrNull(macroScores?.[matchedKey]?.score);
  return parsedMatched != null ? parsedMatched : null;
};

const normalizeHeatmapRows = (data) => {
  if (!data) return [];

  if (Array.isArray(data)) {
    return data
      .map((item) => {
        const marketCode = item?.market || item?.id || item?.source;
        return {
          market: marketCode,
          country: item?.country,
          influence_score: toNumberOrNull(item?.influence_score),
          correlation_score: toNumberOrNull(item?.correlation_score),
          granger_score: toNumberOrNull(item?.granger_score),
          var_score: toNumberOrNull(item?.var_score),
          lag_days: toNumberOrNull(item?.lag_days),
          p_value: toNumberOrNull(item?.p_value),
        };
      })
      .filter((item) => item.market);
  }

  const nodes = Array.isArray(data?.nodes) ? data.nodes : [];
  const edges = Array.isArray(data?.edges) ? data.edges : [];

  if (!nodes.length && !edges.length) return [];

  // Backward compatibility for legacy node-edge payloads.
  const indiaNode = nodes.find((node) => String(node?.id).toLowerCase() === "india");
  const targetId = indiaNode?.id || "india";

  const rows = edges
    .filter((edge) => edge?.source === targetId || edge?.target === targetId)
    .map((edge) => {
      const market = edge.source === targetId ? edge.target : edge.source;
      const influence = toNumberOrNull(edge?.weight);
      return {
        market,
        country: formatLabel(String(market || "")),
        influence_score: influence == null ? null : Math.abs(influence),
        correlation_score: influence,
        granger_score: null,
        var_score: null,
        lag_days: null,
        p_value: null,
      };
    });

  return rows.filter((item) => item.market && String(item.market).toLowerCase() !== "india");
};

const ContagionNetwork = ({ data, macroScores = {} }) => {
  const rows = useMemo(
    () =>
      normalizeHeatmapRows(data).sort(
        (a, b) => (b?.influence_score ?? -Infinity) - (a?.influence_score ?? -Infinity)
      ),
    [data]
  );

  const rowsWithIso = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        iso3: resolveIso3(row),
        macro_score:
          toNumberOrNull(row?.macro_score) ?? toNumberOrNull(row?.macroStressScore) ?? resolveMacroScore(row?.market, macroScores),
      })),
    [rows, macroScores]
  );

  const mappedRows = useMemo(
    () => rowsWithIso.filter((row) => row.iso3 && row.influence_score != null),
    [rowsWithIso]
  );

  const unmappedRows = useMemo(() => rowsWithIso.filter((row) => !row.iso3), [rowsWithIso]);

  const mapTrace = useMemo(() => {
    if (!mappedRows.length) return [];

    return [
      {
        type: "choropleth",
        locationmode: "ISO-3",
        locations: mappedRows.map((row) => row.iso3),
        z: mappedRows.map((row) => clamp(row.influence_score ?? 0, 0, 1)),
        zmin: 0,
        zmax: 1,
        colorscale: [
          [0, "#facc15"],
          [0.5, "#f97316"],
          [1, "#dc2626"],
        ],
        marker: {
          line: { color: "rgba(15, 23, 42, 0.8)", width: 0.6 },
        },
        colorbar: {
          title: "Influence",
          titleside: "top",
          tickvals: [0, 0.5, 1],
          ticktext: ["Low(0.00)", "Medium(0.50)", "High(1.00)"],
          tickcolor: "#ffffff",
          titlefont: { color: "#ffffff" },
          tickfont: { color: "#ffffff" },
        },
        customdata: mappedRows.map((row) => [
          row.country || formatLabel(row.market),
          formatNumeric(row.influence_score),
          formatNumeric(row.correlation_score),
          row.macro_score == null ? "N/A" : formatNumeric(row.macro_score, 2),
        ]),
        hovertemplate:
          "<b>%{customdata[0]} -> India</b><br>" +
          "Influence Score: %{customdata[1]}<br>" +
          "Correlation Score: %{customdata[2]}<br>" +
          "Macro Score: %{customdata[3]}<extra></extra>",
      },
    ];
  }, [mappedRows]);

  const mapLayout = useMemo(
    () => ({
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: { t: 8, r: 16, b: 8, l: 16 },
      dragmode: false,
      geo: {
        projection: { type: "equirectangular" },
        bgcolor: "rgba(0,0,0,0)",
        showframe: false,
        showcoastlines: false,
        showland: true,
        landcolor: "rgba(148, 163, 184, 0.20)",
        showcountries: true,
        countrycolor: "rgba(15, 23, 42, 0.7)",
        showocean: true,
        oceancolor: "rgba(15, 23, 42, 0.32)",
      },
      font: { color: "#ffffff", family: "Inter" },
    }),
    []
  );

  const mapConfig = useMemo(
    () => ({
      responsive: true,
      displayModeBar: false,
      scrollZoom: false,
      doubleClick: false,
    }),
    []
  );

  if (!rows.length || !mappedRows.length) {
    return (
      <div className="rounded-xl border border-neon-green/20 bg-black/20 p-8 text-center">
        <h3 className="text-lg font-semibold text-white mb-2">India-Centric Global Influence Map</h3>
        <p className="text-sm text-gray-300">No country-level influence data is available yet. Please refresh after data processing completes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-white">India-Centric Global Influence Map</h3>
        <p className="text-sm text-gray-300 mt-1">Target Market: India. Hover each highlighted country to inspect influence, correlation, and macro score.</p>
      </div>

      <div className="rounded-xl border border-neon-green/20 bg-slate-950/40 p-2 md:p-4">
        <Suspense fallback={<div className="h-[420px] flex items-center justify-center text-gray-300">Loading map...</div>}>
          <Plot
            data={mapTrace}
            layout={mapLayout}
            config={mapConfig}
            style={{ width: "100%", height: 420 }}
            useResizeHandler={true}
          />
        </Suspense>
      </div>

      {!!unmappedRows.length && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">Not Mapped To Country Geometry</p>
          <div className="flex flex-wrap gap-2 text-xs text-gray-300">
            {unmappedRows.map((row) => (
              <span key={String(row.market)} className="rounded-full border border-white/15 px-2 py-1">
                {(row.country || formatLabel(row.market))}: {formatNumeric(row.influence_score)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContagionNetwork;
