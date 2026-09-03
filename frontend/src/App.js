import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  Line,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./App.css";

const API_BASE = "http://localhost:8000";

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function prepareForecast(rows) {
  return rows.map((r) => ({
    ...r,
    band: [r.lower_bound, r.upper_bound],
    label: formatTime(r.timestamp),
  }));
}

function MetricPanel({ label, value, unit, accent, channel }) {
  return (
    <div className="metric-panel">
      <div className="metric-panel-head">
        <span className="channel-tag" style={{ color: accent }}>
          {channel}
        </span>
        <span className="metric-label">{label}</span>
      </div>
      <div className="metric-value" style={{ color: accent }}>
        {value != null ? value.toFixed(2) : "--"}
        <span className="metric-unit">{unit}</span>
      </div>
    </div>
  );
}

function ForecastPanel({ title, channel, accent, data }) {
  return (
    <div className="forecast-panel">
      <div className="forecast-panel-head">
        <span className="channel-tag" style={{ color: accent }}>
          {channel}
        </span>
        <span className="metric-label">{title}</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 24, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#1C232B" strokeDasharray="0" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#6B7684", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}
            axisLine={{ stroke: "#232B33" }}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            tick={{ fill: "#6B7684", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: "#12171D",
              border: "1px solid #232B33",
              borderRadius: 4,
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: 12,
            }}
            labelStyle={{ color: "#8A97A3" }}
          />
          <Area
            dataKey="band"
            stroke="none"
            fill={accent}
            fillOpacity={0.12}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke={accent}
            strokeWidth={1.75}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function App() {
  const [liveMetrics, setLiveMetrics] = useState(null);
  const [forecast, setForecast] = useState({ cpu: [], memory: [] });
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    const fetchLiveMetrics = async () => {
      try {
        const res = await fetch(`${API_BASE}/live-metrics`);
        const data = await res.json();
        setLiveMetrics(data);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        setError("Cannot reach API — is the backend running?");
      }
    };
    fetchLiveMetrics();
    const interval = setInterval(fetchLiveMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        const res = await fetch(`${API_BASE}/forecast?steps=48`);
        const data = await res.json();
        setForecast({
          cpu: prepareForecast(data.cpu),
          memory: prepareForecast(data.memory),
        });
      } catch (err) {
        setError("Cannot reach API — is the backend running?");
      }
    };
    fetchForecast();
  }, []);

  return (
    <div className="App">
      <header className="app-header">
        <div className="app-title-row">
          <span className={`pulse-dot ${error ? "pulse-dot-off" : ""}`} />
          <h1>Infrastructure Monitor</h1>
        </div>
        <div className="app-meta">
          {error ? (
            <span className="meta-error">{error}</span>
          ) : (
            <span>
              last updated{" "}
              {lastUpdated
                ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                : "--"}
            </span>
          )}
        </div>
      </header>

      <section className="metrics-row">
        <MetricPanel
          label="CPU usage"
          value={liveMetrics?.cpu}
          unit="%"
          accent="#5EEAD4"
          channel="CH.01"
        />
        <MetricPanel
          label="Memory available"
          value={liveMetrics?.memory}
          unit="%"
          accent="#FBBF24"
          channel="CH.02"
        />
      </section>

      <section className="forecast-row">
        <ForecastPanel
          title="CPU forecast — next 4h"
          channel="CH.01"
          accent="#5EEAD4"
          data={forecast.cpu}
        />
        <ForecastPanel
          title="Memory forecast — next 4h"
          channel="CH.02"
          accent="#FBBF24"
          data={forecast.memory}
        />
      </section>
    </div>
  );
}

export default App;