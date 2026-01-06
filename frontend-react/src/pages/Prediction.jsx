import React, { useState } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Button, Badge } from "../components/ui";
import { motion } from "framer-motion";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

// Mock Data
const MOCK_FORECAST = {
  forecast_timestamp: new Date().toISOString(),
  predictions: {
    ph: 7.1,
    turbidity: 680,
    temperature: 24.5,
    do_level: 5.8,
  },
};

const MOCK_TSF = {
  ph_forecast: { horizon_hours: 12, value: 7.05, rationale: "Sample outlook." },
  do_forecast: {
    horizon_hours: 24,
    value: 5.9,
    rationale: "Sample DO projection.",
  },
  turbidity_pattern: { expected_value: 640, rationale: "Visual baseline." },
  temperature_spike: { expected_value: 25.4, rationale: "Mock summer spike." },
  health_index: {
    next_value: 0.87,
    trend: "steady",
    rationale: "Composite based on mock inputs.",
  },
};

export const Prediction = () => {
  const [status, setStatus] = useState("Ready");
  const [data, setData] = useState(null);
  const [tsf, setTsf] = useState(null);

  const handleRunForecast = async () => {
    setStatus("Running Forecast...");
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1000));
    setData(MOCK_FORECAST);
    setTsf(MOCK_TSF);
    setStatus("Ready");
  };

  const chartData = data
    ? {
        labels: ["pH", "Turbidity (x100)", "Temp", "DO"],
        datasets: [
          {
            label: "Forecast Values",
            data: [
              data.predictions.ph,
              data.predictions.turbidity / 100,
              data.predictions.temperature,
              data.predictions.do_level,
            ],
            backgroundColor: ["#3b82f6", "#06b6d4", "#10b981", "#f59e0b"],
            borderRadius: 4,
          },
        ],
      }
    : null;

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
    },
    scales: {
      y: { beginAtZero: true, grid: { color: "#e2e8f0" } },
      x: { grid: { display: false } },
    },
  };

  return (
    <AppLayout title="Prediction Lab">
      <Card className="mb-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>
              Temporal Fusion Transformer
            </h3>
            <p className="text-muted" style={{ fontSize: "0.9rem" }}>
              Generate outlook for pH, Turbidity, and DO levels.
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div
              className="flex items-center gap-2 text-muted"
              style={{ fontSize: "0.9rem" }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--success)",
                }}
              ></span>
              <span>{status}</span>
            </div>
            <Button variant="primary" onClick={handleRunForecast}>
              Run Forecast
            </Button>
          </div>
        </div>
      </Card>

      <div className="grid-2">
        <div className="flex flex-col gap-4">
          <Card style={{ flex: 1, minHeight: 400 }}>
            <div className="card-title mb-4">Projected Values (Next 12h)</div>
            {data ? (
              <div style={{ height: 300 }}>
                <Bar data={chartData} options={chartOptions} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted">
                Click 'Run Forecast' to view data
              </div>
            )}
          </Card>

          <div className="grid-2">
            <Card>
              <div className="text-muted label">pH Trend</div>
              <div style={{ fontSize: "2rem", fontWeight: 700 }}>
                {data ? data.predictions.ph : "--"}
              </div>
              <Badge variant="neutral">
                {data ? (data.predictions.ph >= 7 ? "Basic" : "Acidic") : "--"}
              </Badge>
            </Card>
            <Card>
              <div className="text-muted label">Turbidity</div>
              <div style={{ fontSize: "2rem", fontWeight: 700 }}>
                {data ? data.predictions.turbidity : "--"}
              </div>
              <Badge variant="neutral">
                {data
                  ? data.predictions.turbidity > 600
                    ? "High"
                    : "Normal"
                  : "--"}
              </Badge>
            </Card>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <Card style={{ flex: 1 }}>
            <div className="card-title mb-4">Hackathon Insights (TSF)</div>
            {tsf ? (
              <div className="flex flex-col gap-4">
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                  style={{
                    paddingBottom: 16,
                    borderBottom: "1px solid var(--border-color)",
                  }}
                >
                  <div className="flex justify-between mb-2">
                    <span className="label">pH Drift Horizon</span>
                    <Badge variant="neutral">
                      {tsf.ph_forecast.horizon_hours}h
                    </Badge>
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 600 }}>
                    {tsf.ph_forecast.value}
                  </div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    {tsf.ph_forecast.rationale}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  style={{
                    paddingBottom: 16,
                    borderBottom: "1px solid var(--border-color)",
                  }}
                >
                  <div className="flex justify-between mb-2">
                    <span className="label">DO Projection</span>
                    <Badge variant="neutral">
                      {tsf.do_forecast.horizon_hours}h
                    </Badge>
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 600 }}>
                    {tsf.do_forecast.value}
                  </div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    {tsf.do_forecast.rationale}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="label">Interpretation Narrative</div>
                  <div
                    style={{
                      padding: 12,
                      background: "var(--bg-body)",
                      borderRadius: "var(--radius-md)",
                      fontSize: "0.9rem",
                      lineHeight: 1.5,
                      border: "1px solid var(--border-color)",
                    }}
                  >
                    Forecast Analysis: pH expected to reach{" "}
                    {tsf.ph_forecast.value} in {tsf.ph_forecast.horizon_hours}h.
                    Overall health index is {tsf.health_index.trend}.
                  </div>
                </motion.div>
              </div>
            ) : (
              <div className="text-muted">Waiting for forecast run...</div>
            )}
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};
