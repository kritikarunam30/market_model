import { Suspense, useEffect, useMemo, useState } from 'react';
import LoadingSpinner from './LoadingSpinner';
import PlotModule from "react-plotly.js";
import { fetchRiskIndex } from '../api/marketApi';

const Plot = PlotModule?.default?.default ?? PlotModule?.default ?? PlotModule;

const COLOR_BY_RISK = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#ef4444',
};

const formatDate = (value) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value ?? '');
  return parsed.toISOString().slice(0, 10);
};

const PlotlyChart = ({ history = [], loading = false, error = '', height = 360, className = '' }) => {
  const [localHistory, setLocalHistory] = useState([]);
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState('');

  const hasExternalHistory = Array.isArray(history) && history.length > 0;

  useEffect(() => {
    if (hasExternalHistory) return;

    let isMounted = true;
    const loadRiskHistory = async () => {
      setLocalLoading(true);
      setLocalError('');
      try {
        const response = await fetchRiskIndex();
        if (!isMounted) return;
        setLocalHistory(Array.isArray(response?.history) ? response.history : []);
      } catch (loadErr) {
        if (!isMounted) return;
        setLocalError(loadErr?.response?.data?.detail || loadErr?.message || 'Failed to load risk data');
      } finally {
        if (isMounted) setLocalLoading(false);
      }
    };

    loadRiskHistory();

    return () => {
      isMounted = false;
    };
  }, [hasExternalHistory]);

  const effectiveHistory = hasExternalHistory ? history : localHistory;
  const displayLoading = Boolean(loading || (!hasExternalHistory && localLoading));
  const displayError = error || (!hasExternalHistory ? localError : '');

  const chartData = useMemo(() => {
    const points = (Array.isArray(effectiveHistory) ? effectiveHistory : [])
      .filter((row) => row && row.date && row.risk_index != null)
      .map((row) => ({
        date: new Date(row.date).toISOString(),
        dateLabel: formatDate(row.date),
        riskIndex: Number(row.risk_index),
        riskLabel: String(row.risk_label ?? '').toLowerCase(),
      }))
      .filter((row) => Number.isFinite(row.riskIndex));

    if (!points.length) {
      return { traces: [], lineColor: COLOR_BY_RISK.low };
    }

    const latest = points[points.length - 1];
    const lineColor = COLOR_BY_RISK[latest.riskLabel] ?? COLOR_BY_RISK.medium;

    return {
      lineColor,
      traces: [
        {
          x: points.map((point) => point.date),
          y: points.map((point) => point.riskIndex),
          customdata: points.map((point) => point.dateLabel),
          type: 'scatter',
          mode: 'lines+markers',
          line: {
            color: lineColor,
            width: 3,
            shape: 'spline',
            smoothing: 1,
          },
          marker: {
            size: 8,
            opacity: 0,
            color: lineColor,
          },
          hovertemplate: 'Date: %{customdata}<br>Risk Index: %{y:.2f}<extra></extra>',
          name: 'Risk Index',
        },
        {
          x: [latest.date],
          y: [latest.riskIndex],
          customdata: [latest.dateLabel],
          type: 'scatter',
          mode: 'markers',
          marker: {
            size: 10,
            color: lineColor,
            line: { width: 2, color: '#ffffff' },
          },
          hovertemplate: 'Latest<br>Date: %{customdata}<br>Risk Index: %{y:.2f}<extra></extra>',
          name: 'Latest Point',
        },
      ],
    };
  }, [effectiveHistory]);

  const layout = useMemo(
    () => ({
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(10,10,10,0.65)',
      font: { color: '#ffffff', family: 'Inter' },
      margin: { t: 20, r: 16, b: 56, l: 64 },
      dragmode: false,
      hovermode: 'closest',
      hoverdistance: 100,
      spikedistance: -1,
      xaxis: {
        title: { text: 'Date' },
        type: 'date',
        tickformat: '%Y-%m-%d',
        gridcolor: 'rgba(255, 255, 255, 0.10)',
        zerolinecolor: 'rgba(255, 255, 255, 0.15)',
        automargin: true,
      },
      yaxis: {
        title: { text: 'Risk Index' },
        gridcolor: 'rgba(255, 255, 255, 0.10)',
        zerolinecolor: 'rgba(255, 255, 255, 0.15)',
        tickformat: '.2f',
        automargin: true,
      },
    }),
    []
  );

  const config = useMemo(
    () => ({
      displayModeBar: false,
      responsive: true,
      scrollZoom: false,
      doubleClick: false,
    }),
    []
  );

  if (displayLoading) {
    return (
      <div className={`w-full rounded-xl shadow-lg bg-black/25 p-4 md:p-6 ${className}`}>
        <h3 className="text-xl font-semibold text-white mb-3">Risk Index Over Time</h3>
        <LoadingSpinner message="Loading risk chart..." />
      </div>
    );
  }

  if (displayError) {
    return (
      <div className={`w-full rounded-xl shadow-lg bg-black/25 p-4 md:p-6 ${className}`}>
        <h3 className="text-xl font-semibold text-white mb-3">Risk Index Over Time</h3>
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
          Failed to load risk chart data: {displayError}
        </div>
      </div>
    );
  }

  if (!chartData.traces.length) {
    return (
      <div className={`w-full rounded-xl shadow-lg bg-black/25 p-4 md:p-6 ${className}`}>
        <h3 className="text-xl font-semibold text-white mb-3">Risk Index Over Time</h3>
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm text-gray-300">
          No risk history available.
        </div>
      </div>
    );
  }

  return (
    <Suspense fallback={<LoadingSpinner message="Loading chart..." />}>
      <div className={`w-full rounded-xl shadow-lg bg-black/25 p-4 md:p-6 ${className}`}>
        <h3 className="text-xl font-semibold text-white mb-3">Risk Index Over Time</h3>
        <Plot
          data={chartData.traces}
          layout={layout}
          config={config}
          style={{ width: '100%', height }}
          useResizeHandler={true}
        />
      </div>
    </Suspense>
  );
};

export default PlotlyChart;
