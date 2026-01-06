import React, { useState, useEffect } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Button, Badge } from "../components/ui";
import { motion } from "framer-motion";
import Plot from "react-plotly.js";

export const Research = () => {
  const [status, setStatus] = useState("Ready to compute");
  const [data, setData] = useState(null);

  const handleRunAnalysis = () => {
    setStatus("Running analysis...");
    setTimeout(() => {
      setData({
        // Mock data triggering renders
        gnn: true,
        bayesian: true,
        propagation: true,
      });
      setStatus("Analysis Complete");
    }, 800);
  };

  // --- GNN CHART ---
  const renderGNN = () => {
    const lakeShape = {
      type: "path",
      path: "M 0.2,0.5 Q 0.2,0.8 0.5,0.9 Q 0.8,0.8 0.8,0.5 Q 0.8,0.2 0.5,0.1 Q 0.2,0.2 0.2,0.5 Z",
      fillcolor: "rgba(59, 130, 246, 0.05)",
      line: { color: "rgba(59, 130, 246, 0.2)", width: 2 },
    };
    const sensorPositions = {
      "S-01": { x: 0.35, y: 0.8 },
      "S-02": { x: 0.65, y: 0.8 },
      "S-03": { x: 0.85, y: 0.5 },
      "S-04": { x: 0.65, y: 0.2 },
      "S-05": { x: 0.35, y: 0.2 },
      "S-06": { x: 0.15, y: 0.5 },
    };
    const edgeTraces = [];
    const connections = [
      ["S-01", "S-02"],
      ["S-02", "S-03"],
      ["S-03", "S-04"],
      ["S-04", "S-05"],
      ["S-05", "S-06"],
      ["S-06", "S-01"],
      ["S-01", "S-04"],
    ];

    connections.forEach((c) => {
      edgeTraces.push({
        x: [sensorPositions[c[0]].x, sensorPositions[c[1]].x],
        y: [sensorPositions[c[0]].y, sensorPositions[c[1]].y],
        mode: "lines",
        line: { width: 1, color: "#e2e8f0" },
        type: "scatter",
        showlegend: false,
        hoverinfo: "none",
      });
    });

    const nodeTrace = {
      x: Object.values(sensorPositions).map((p) => p.x),
      y: Object.values(sensorPositions).map((p) => p.y),
      mode: "markers+text",
      marker: {
        size: 24,
        color: "#ffffff",
        line: { width: 2, color: "#3b82f6" },
      },
      text: Object.keys(sensorPositions),
      textposition: "top center",
      type: "scatter",
      hoverinfo: "text",
    };

    return (
      <Plot
        data={[...edgeTraces, nodeTrace]}
        layout={{
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { family: "Inter", color: "#64748b" },
          margin: { l: 20, r: 20, t: 20, b: 20 },
          xaxis: { visible: false, range: [0, 1] },
          yaxis: { visible: false, range: [0, 1] },
          shapes: [lakeShape],
          showlegend: false,
          height: 400,
          autosize: true,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "100%" }}
      />
    );
  };

  // --- BAYESIAN CHART ---
  const renderBayesian = () => {
    const x = Array.from({ length: 24 }, (_, i) => i);
    const y = x.map((i) => 7 + Math.sin(i / 3));
    const yUpper = y.map((v) => v + 0.5);
    const yLower = y.map((v) => v - 0.5);

    return (
      <Plot
        data={[
          {
            x: x,
            y: yUpper,
            type: "scatter",
            mode: "lines",
            line: { width: 0 },
            showlegend: false,
            hoverinfo: "skip",
          },
          {
            x: x,
            y: yLower,
            type: "scatter",
            mode: "lines",
            fill: "tonexty",
            fillcolor: "rgba(59, 130, 246, 0.2)",
            line: { width: 0 },
            showlegend: false,
            hoverinfo: "skip",
          },
          {
            x: x,
            y: y,
            type: "scatter",
            mode: "lines",
            line: { color: "#3b82f6", width: 3 },
            name: "Median",
          },
        ]}
        layout={{
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { family: "Inter", color: "#64748b" },
          margin: { l: 40, r: 20, t: 20, b: 40 },
          yaxis: { title: "DO (mg/L)", gridcolor: "#e2e8f0" },
          xaxis: { title: "Hours Ahead" },
          height: 350,
          autosize: true,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "100%" }}
      />
    );
  };

  // --- PROPAGATION CHART ---
  const renderPropagation = () => {
    const sensors = ["S-01", "S-02", "S-03", "S-04", "S-05", "S-06"];
    return (
      <Plot
        data={[
          {
            x: sensors,
            y: [8.2, 7.9, 7.5, 6.8, 6.5, 7.1],
            type: "scatter",
            mode: "lines+markers",
            line: { color: "#8b5cf6", width: 2 },
            marker: {
              size: 8,
              color: "#ffffff",
              line: { width: 2, color: "#8b5cf6" },
            },
          },
        ]}
        layout={{
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { family: "Inter", color: "#64748b" },
          margin: { l: 40, r: 20, t: 20, b: 40 },
          yaxis: { title: "Projected Impact", gridcolor: "#e2e8f0" },
          xaxis: { gridcolor: "transparent" },
          height: 350,
          autosize: true,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "100%" }}
      />
    );
  };

  return (
    <AppLayout title="Research Models">
      <Card className="mb-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>
              Advanced Lake Ecosystem Analysis
            </h3>
            <p className="text-muted" style={{ fontSize: "0.9rem" }}>
              Trigger Graph Neural Networks and Causal Inference engines.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-muted" style={{ fontSize: "0.85rem" }}>
              {status}
            </span>
            <Button variant="primary" onClick={handleRunAnalysis}>
              Run Analysis
            </Button>
          </div>
        </div>
      </Card>

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card mb-4"
      >
        <div className="card-title mb-4">
          GNN Sensor Topology & Risk Propagation
        </div>
        <div style={{ height: 400 }}>
          {data ? (
            renderGNN()
          ) : (
            <div className="flex justify-center items-center h-full text-muted">
              Click 'Run Analysis' to visualize network topology
            </div>
          )}
        </div>
      </motion.div>

      <div className="grid-2">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <div className="card-title mb-4">
              Bayesian DO Forecast (Probabilistic)
            </div>
            <div style={{ height: 350 }}>
              {data ? (
                renderBayesian()
              ) : (
                <div className="flex justify-center items-center h-full text-muted">
                  Waiting...
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <div className="card-title mb-4">Multi-Horizon Propagation</div>
            <div style={{ height: 350 }}>
              {data ? (
                renderPropagation()
              ) : (
                <div className="flex justify-center items-center h-full text-muted">
                  Waiting...
                </div>
              )}
            </div>
          </Card>
        </motion.div>
      </div>
    </AppLayout>
  );
};
