import React, { useState } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Button, Input, Badge } from "../components/ui";
import { motion, AnimatePresence } from "framer-motion";

const ResultItem = ({ title, data }) => {
  const sentiment = data.confidence.toLowerCase().includes("high")
    ? "success"
    : data.confidence.toLowerCase().includes("low")
    ? "danger"
    : "warning";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        padding: 16,
        border: "1px solid var(--border-color)",
        borderRadius: "var(--radius-md)",
        background: "var(--bg-surface)",
      }}
    >
      <div className="flex justify-between items-center mb-2">
        <span style={{ fontWeight: 600, color: "var(--text-main)" }}>
          {title}
        </span>
        <Badge variant={sentiment}>{data.confidence} Confidence</Badge>
      </div>
      <p
        style={{
          color: "var(--text-secondary)",
          fontSize: "0.875rem",
          marginBottom: 8,
        }}
      >
        {data.description}
      </p>
      <div
        className="flex items-start gap-2 text-muted"
        style={{ fontSize: "0.75rem" }}
      >
        <span>⚠️</span>
        <span>{data.impact}</span>
      </div>
    </motion.div>
  );
};

export const Simulation = () => {
  const [status, setStatus] = useState("Waiting for input");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [formData, setFormData] = useState({
    tempRise: 1.5,
    pollution: 0.35,
    rainfall: 20,
  });

  const handleRunSim = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus("Running Model...");

    // Mock API Call
    await new Promise((r) => setTimeout(r, 1000));

    setResults({
      do: {
        description: "DO levels expected to drop by 18% in lower strata.",
        impact: "Risk of hypoxia for benthic organisms.",
        confidence: "High",
      },
      pollution: {
        description: "Contaminant plume will disperse within 6 hours.",
        impact: "Temporary spike in turbidity at outlet.",
        confidence: "Medium",
      },
      eco: {
        description: "Algal bloom probability increased by 22%.",
        impact: "Monitor chlorophyll-a levels closely.",
        confidence: "Low",
      },
      fish: {
        description: "Fish stress index remains within tolerance.",
        impact: "No acute mortality predicted.",
        confidence: "High",
      },
    });
    setStatus("Analysis Complete");
    setLoading(false);
  };

  return (
    <AppLayout title="Digital Twin Simulation">
      <div className="grid-2">
        {/* Control Panel */}
        <Card>
          <div className="card-title mb-4">Scenario Parameters</div>
          <form
            onSubmit={handleRunSim}
            style={{ display: "flex", flexDirection: "column", gap: 20 }}
          >
            <div>
              <Input
                label="Temperature Rise (°C)"
                type="number"
                step="0.1"
                value={formData.tempRise}
                onChange={(e) =>
                  setFormData({ ...formData, tempRise: e.target.value })
                }
              />
              <div
                className="text-muted"
                style={{ fontSize: "0.85rem", marginTop: 4 }}
              >
                Projected increase above baseline
              </div>
            </div>

            <div>
              <Input
                label="Pollution Intensity (0-1)"
                type="number"
                step="0.05"
                value={formData.pollution}
                onChange={(e) =>
                  setFormData({ ...formData, pollution: e.target.value })
                }
              />
              <div
                className="text-muted"
                style={{ fontSize: "0.85rem", marginTop: 4 }}
              >
                Severity of chemical influx
              </div>
            </div>

            <div>
              <Input
                label="Rainfall (mm/24h)"
                type="number"
                step="1"
                value={formData.rainfall}
                onChange={(e) =>
                  setFormData({ ...formData, rainfall: e.target.value })
                }
              />
              <div
                className="text-muted"
                style={{ fontSize: "0.85rem", marginTop: 4 }}
              >
                Stormwater runoff volume
              </div>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                paddingTop: 16,
                borderTop: "1px solid var(--border-color)",
              }}
            >
              <Button type="submit" variant="primary" disabled={loading}>
                {loading ? "Processing..." : "Run Simulation"}
              </Button>
            </div>
          </form>
        </Card>

        {/* Results Panel */}
        <Card style={{ minHeight: 480 }}>
          <div className="flex justify-between items-center mb-4">
            <div className="card-title">Projected Impact</div>
            <Badge
              variant={loading ? "primary" : results ? "success" : "neutral"}
            >
              {status}
            </Badge>
          </div>

          <div className="flex flex-col gap-4">
            {results ? (
              <AnimatePresence>
                <ResultItem title="DO Drop Scenario" data={results.do} />
                <ResultItem
                  title="Pollution Response"
                  data={results.pollution}
                />
                <ResultItem title="Ecological Risk" data={results.eco} />
                <ResultItem title="Fauna Impact" data={results.fish} />
              </AnimatePresence>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: 260,
                  color: "var(--text-muted)",
                }}
              >
                <div
                  style={{ fontSize: "3rem", opacity: 0.2, marginBottom: 16 }}
                >
                  ⚡
                </div>
                <p>Configure parameters and run to see impact analysis.</p>
              </div>
            )}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
};
