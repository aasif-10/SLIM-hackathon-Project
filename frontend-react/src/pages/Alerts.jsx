import React, { useState } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Badge } from "../components/ui";
import { motion, AnimatePresence } from "framer-motion";

const MOCK_ALERTS = [
  {
    id: 1,
    title: "Low Dissolved Oxygen",
    sensor: "S-04 South Inlet",
    severity: "high",
    description: "DO level dropped to 3.2 mg/L, below critical threshold.",
    time: "2m ago",
    metrics: { do: "3.2 mg/L", temp: "29.1C" },
  },
  {
    id: 2,
    title: "Turbidity Spike",
    sensor: "S-04 South Inlet",
    severity: "high",
    description: "Reading of 485 NTU detected. Potential polluted inflow.",
    time: "8m ago",
    metrics: { turbidity: "485 NTU", change: "+304%" },
  },
  {
    id: 3,
    title: "pH Level Drift",
    sensor: "S-03 Central Deep",
    severity: "medium",
    description: "pH decreased from 7.4 to 6.8 over past 3 hours.",
    time: "15m ago",
    metrics: { ph: "6.8", rate: "-0.2/hr" },
  },
  {
    id: 4,
    title: "Temp Anomaly",
    sensor: "S-02 East Bay",
    severity: "medium",
    description: "Water temp +3.2C above daily average.",
    time: "23m ago",
    metrics: { temp: "24.5C", avg: "21.3C" },
  },
  {
    id: 6,
    title: "Rainfall Impact",
    sensor: "Network-wide",
    severity: "low",
    description: "Heavy rainfall (32mm) detected. Monitoring runoff.",
    time: "1h ago",
    metrics: { rainfall: "32mm", rain_duration: "6 hrs" },
  },
  {
    id: 7,
    title: "Calibration Due",
    sensor: "S-05 West Shore",
    severity: "low",
    description: "pH sensor calibration due in 48 hours.",
    time: "2h ago",
    metrics: { lastCal: "28d ago", status: "Due Soon" },
  },
  {
    id: 8,
    title: "Normal Ops",
    sensor: "S-01 North Shore",
    severity: "none",
    description: "All parameters normal.",
    time: "3h ago",
    metrics: { status: "Optimal" },
  },
];

const AlertCard = ({ alert, index }) => {
  const borderColors = {
    high: "var(--danger)",
    medium: "var(--warning)",
    low: "var(--primary)",
    none: "var(--success)",
  };

  const severityVariant = {
    high: "danger",
    medium: "warning",
    low: "neutral",
    none: "success",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card
        style={{
          borderLeft: `4px solid ${borderColors[alert.severity]}`,
          marginBottom: 0,
        }}
      >
        <div className="flex justify-between items-center mb-2">
          <div style={{ fontWeight: 600, color: "var(--text-main)" }}>
            {alert.title}
          </div>
          <Badge variant={severityVariant[alert.severity]}>
            {alert.severity.toUpperCase()}
          </Badge>
        </div>
        <div
          className="text-muted"
          style={{ fontSize: "0.8rem", marginBottom: 8 }}
        >
          {alert.sensor} • {alert.time}
        </div>
        <p style={{ fontSize: "0.9rem", marginBottom: 12 }}>
          {alert.description}
        </p>
        <div
          style={{
            background: "var(--bg-body)",
            padding: 8,
            borderRadius: "var(--radius-sm)",
          }}
        >
          <div
            className="flex flex-wrap gap-4"
            style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
          >
            {Object.entries(alert.metrics).map(([k, v]) => (
              <div key={k} className="flex gap-1">
                <span style={{ fontWeight: 500, color: "var(--text-main)" }}>
                  {k}:
                </span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </motion.div>
  );
};

export const Alerts = () => {
  const counts = { high: 0, medium: 0, low: 0, none: 0 };
  MOCK_ALERTS.forEach((a) => counts[a.severity]++);

  const sortedAlerts = [...MOCK_ALERTS].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2, none: 3 };
    return order[a.severity] - order[b.severity];
  });

  return (
    <AppLayout title="Event Scanner">
      {/* Summary Stats */}
      <Card className="mb-4">
        <div className="flex justify-around items-center px-4">
          <div className="text-center">
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--danger)",
              }}
            >
              {counts.high}
            </div>
            <div className="text-muted text-xs uppercase tracking-wider">
              Critical
            </div>
          </div>
          <div className="text-center">
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--warning)",
              }}
            >
              {counts.medium}
            </div>
            <div className="text-muted text-xs uppercase tracking-wider">
              Warning
            </div>
          </div>
          <div className="text-center">
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--primary)",
              }}
            >
              {counts.low}
            </div>
            <div className="text-muted text-xs uppercase tracking-wider">
              Info
            </div>
          </div>
          <div className="text-center">
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--success)",
              }}
            >
              {counts.none}
            </div>
            <div className="text-muted text-xs uppercase tracking-wider">
              Clear
            </div>
          </div>
        </div>
      </Card>

      <div className="grid-2 gap-4">
        {sortedAlerts.map((alert, idx) => (
          <AlertCard key={alert.id} alert={alert} index={idx} />
        ))}
      </div>
    </AppLayout>
  );
};
