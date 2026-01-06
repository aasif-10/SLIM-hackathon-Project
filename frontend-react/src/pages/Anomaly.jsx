import React, { useEffect, useState } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card } from "../components/ui";
// import Plot from 'react-plotly.js'; // Commenting out to debug route

// Dynamic import strategy for Plotly could be used here, but for now let's ensure the route loads.
// Using a placeholder heatmap visualization instead of full Plotly to guarantee stability.

export const Anomaly = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Generate a 10x24 grid of data
    const grid = [];
    for (let i = 0; i < 6; i++) {
      const row = [];
      for (let j = 0; j < 24; j++) {
        row.push(Math.random());
      }
      grid.push(row);
    }
    setData(grid);
  }, []);

  const StatusChip = ({ l, s, v }) => (
    <div
      style={{
        border: "1px solid var(--border-color)",
        padding: "12px 20px",
        borderRadius: 8,
        minWidth: 140,
        background: "var(--bg-surface)",
      }}
    >
      <div className="text-muted" style={{ fontSize: "0.85rem" }}>
        {l}
      </div>
      <div style={{ fontSize: "1.25rem", fontWeight: 600, marginTop: 4 }}>
        {v}
      </div>
      <span
        style={{
          display: "inline-block",
          marginTop: 8,
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: `var(--${
            s === "danger" ? "danger" : s === "warning" ? "warning" : "success"
          })`,
        }}
      />
    </div>
  );

  return (
    <AppLayout title="Anomaly Lab">
      {/* Stats Row */}
      <div className="grid-4 mb-4">
        <Card>
          <div className="text-muted label">Critical Anomalies</div>
          <div
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--danger)",
            }}
          >
            3
          </div>
        </Card>
        <Card>
          <div className="text-muted label">Warnings</div>
          <div
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--warning)",
            }}
          >
            8
          </div>
        </Card>
        <Card>
          <div className="text-muted label">Normal Readings</div>
          <div
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--success)",
            }}
          >
            85
          </div>
        </Card>
        <Card>
          <div className="text-muted label">Detection Rate</div>
          <div
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--primary-color)",
            }}
          >
            11.5%
          </div>
        </Card>
      </div>

      {/* CSS Grid Heatmap (Lighter alternative to Plotly for stability) */}
      <div className="mb-4">
        <Card>
          <div className="card-title mb-4">
            Sensor Network Heatmap (Last 24h)
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              gap: 16,
            }}
          >
            {/* Y Axis Labels */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-around",
                paddingBottom: 24,
                fontSize: "0.85rem",
                color: "var(--text-muted)",
              }}
            >
              {["S-01", "S-02", "S-03", "S-04", "S-05", "S-06"].map((s) => (
                <div key={s}>{s}</div>
              ))}
            </div>

            {/* Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateRows: "repeat(6, 1fr)",
                gap: 4,
              }}
            >
              {data.map((row, i) => (
                <div
                  key={i}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(24, 1fr)",
                    gap: 2,
                  }}
                >
                  {row.map((val, j) => (
                    <div
                      key={j}
                      style={{
                        background:
                          val > 0.8
                            ? "var(--danger)"
                            : val > 0.6
                            ? "var(--warning)"
                            : "var(--success)",
                        opacity: val > 0.8 ? val : 0.2 + val * 0.4,
                        borderRadius: 2,
                      }}
                      title={`Hour ${j}: ${val.toFixed(2)}`}
                    ></div>
                  ))}
                </div>
              ))}
              {/* X Axis */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  paddingTop: 8,
                }}
              >
                <span>00:00</span>
                <span>06:00</span>
                <span>12:00</span>
                <span>18:00</span>
                <span>23:00</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Status Chips */}
      <Card>
        <div className="card-title mb-4">Current Sensor Status</div>
        <div className="flex flex-wrap gap-4">
          <StatusChip l="pH" s="success" v="7.4" />
          <StatusChip l="Turbidity" s="danger" v="485" />
          <StatusChip l="Temp" s="primary" v="24.5°" />
          <StatusChip l="DO" s="warning" v="5.2" />
        </div>
      </Card>
    </AppLayout>
  );
};
