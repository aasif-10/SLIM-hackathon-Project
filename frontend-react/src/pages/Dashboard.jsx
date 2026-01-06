import React, { useState } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card, Button, Badge } from "../components/ui";
import { motion } from "framer-motion";
import { LakeMap } from "../components/layout/LakeMap";

// Hardcoded ESP32 live sensor reading
const ESP32_LIVE_READING = {
  sensorId: "ESP32-001",
  name: "ESP32 Main Sensor",
  timestamp: new Date().toLocaleTimeString(),
  temp: 19.4,
  ph: 7.2,
  oxygen: 8.5,
  turbidity: 2.8,
  conductivity: 485,
  tds: 312,
};

// Mock Data
const SENSORS = [
  {
    id: "S-01",
    name: "North Shore",
    status: "healthy",
    lat: 12.9842,
    lng: 77.6185,
  },
  {
    id: "S-02",
    name: "East Bay",
    status: "healthy",
    lat: 12.9838,
    lng: 77.6202,
  },
  {
    id: "S-03",
    name: "Central Deep",
    status: "healthy",
    lat: 12.9828,
    lng: 77.6188,
  },
  {
    id: "S-04",
    name: "South Inlet",
    status: "warning",
    lat: 12.9815,
    lng: 77.6185,
  },
  {
    id: "S-05",
    name: "West Shore",
    status: "healthy",
    lat: 12.9825,
    lng: 77.6172,
  },
  {
    id: "S-06",
    name: "Outlet Channel",
    status: "healthy",
    lat: 12.982,
    lng: 77.6198,
  },
];

const MOCK_READINGS = {
  "S-01": { temp: 18.2, ph: 7.4, oxygen: 8.9, turbidity: 2.1 },
  "S-02": { temp: 18.5, ph: 7.5, oxygen: 9.2, turbidity: 1.8 },
  "S-03": { temp: 17.8, ph: 7.3, oxygen: 8.7, turbidity: 2.4 },
  "S-04": { temp: 19.1, ph: 6.9, oxygen: 7.8, turbidity: 4.2 },
  "S-05": { temp: 18.3, ph: 7.4, oxygen: 9.0, turbidity: 2.2 },
  "S-06": { temp: 18.7, ph: 7.5, oxygen: 8.8, turbidity: 2.6 },
};

const InsightCard = ({
  label,
  value,
  subtext,
  color = "success",
  delay = 0,
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4, delay }}
  >
    <Card>
      <div className="text-xs text-muted uppercase tracking-wide mb-2">
        {label}
      </div>
      <div className="text-2xl font-bold leading-tight">{value}</div>
      <div className="flex items-center gap-2 mt-2 text-sm text-muted">
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: `var(--${color})`,
          }}
        />
        {subtext}
      </div>
    </Card>
  </motion.div>
);

export const Dashboard = () => {
  const [selectedSensorId, setSelectedSensorId] = useState(null);
  const [showReading, setShowReading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleExtractESP32 = () => {
    setIsLoading(true);
    setShowReading(false);
    setTimeout(() => {
      setIsLoading(false);
      setShowReading(true);
    }, 6000);
  };

  const readings = Object.values(MOCK_READINGS);
  const avgTemp = (
    readings.reduce((sum, r) => sum + r.temp, 0) / readings.length
  ).toFixed(1);
  const avgTurbidity = (
    readings.reduce((sum, r) => sum + r.turbidity, 0) / readings.length
  ).toFixed(1);
  const healthyCount = SENSORS.filter((s) => s.status === "healthy").length;

  const selectedSensor = selectedSensorId
    ? SENSORS.find((s) => s.id === selectedSensorId)
    : null;
  const selectedReading = selectedSensorId
    ? MOCK_READINGS[selectedSensorId]
    : null;

  return (
    <AppLayout title="Monitoring Dashboard">
      <div className="grid-3 mb-4">
        <InsightCard
          label="Overall Condition"
          value="Stable"
          subtext={`Avg Temp ${avgTemp}°C`}
          color="success"
          delay={0.1}
        />
        <InsightCard
          label="Avg Turbidity"
          value={`${avgTurbidity} NTU`}
          subtext={avgTurbidity <= 3 ? "Clear Water" : "High Particulates"}
          color={avgTurbidity <= 3 ? "success" : "warning"}
          delay={0.2}
        />
        <InsightCard
          label="Network Status"
          value={`${healthyCount}/${SENSORS.length} Active`}
          subtext="All sensors responding"
          color="success"
          delay={0.3}
        />
      </div>

      <div className="grid-3 mb-4">
        <Card
          className="col-span-2"
          style={{
            gridColumn: "span 2",
            height: 500,
            padding: 0,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            className="card-header"
            style={{
              padding: "var(--space-md) var(--space-lg)",
              borderBottom: "1px solid var(--border-color)",
              zIndex: 10,
              position: "relative",
            }}
          >
            <div>
              <div className="font-semibold">Sensor Network Map</div>
              <div className="text-xs text-muted">Ulsoor Lake Sector</div>
            </div>
          </div>

          <div style={{ flex: 1, height: "calc(100% - 65px)" }}>
            <LakeMap
              sensors={SENSORS}
              selectedId={selectedSensorId}
              onSelect={setSelectedSensorId}
            />
          </div>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <div className="card-header">
              <div className="font-semibold">Live Controls</div>
              <Badge variant="neutral">ESP32</Badge>
            </div>
            <div className="grid-2 gap-2">
              <Button
                size="sm"
                variant="primary"
                onClick={handleExtractESP32}
                disabled={isLoading}
              >
                {isLoading ? "Extracting..." : "Extract ESP32"}
              </Button>
              <Button size="sm" variant="secondary">
                Fetch Cloud
              </Button>
            </div>
          </Card>

          <Card style={{ flex: 1 }}>
            <div className="card-title">Live Sensor Reading</div>
            {isLoading ? (
              <div className="text-center" style={{ padding: "40px 0" }}>
                <div className="text-muted mb-2">Extracting ESP32 data...</div>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  style={{
                    width: 24,
                    height: 24,
                    border: "3px solid var(--border-color)",
                    borderTopColor: "var(--primary)",
                    borderRadius: "50%",
                    margin: "0 auto",
                  }}
                />
              </div>
            ) : showReading ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="flex justify-between items-center mb-4">
                  <h3 style={{ margin: 0 }}>{ESP32_LIVE_READING.name}</h3>
                  <Badge variant="success">Online</Badge>
                </div>
                <div className="text-xs text-muted mb-3">
                  ID: {ESP32_LIVE_READING.sensorId}
                </div>
                <div className="grid-2 gap-4">
                  <div>
                    <div className="label">Temperature</div>
                    <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
                      {ESP32_LIVE_READING.temp}°C
                    </div>
                  </div>
                  <div>
                    <div className="label">pH Level</div>
                    <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
                      {ESP32_LIVE_READING.ph}
                    </div>
                  </div>
                  <div>
                    <div className="label">Dissolved Oxygen</div>
                    <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
                      {ESP32_LIVE_READING.oxygen} mg/L
                    </div>
                  </div>
                  <div>
                    <div className="label">Turbidity</div>
                    <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
                      {ESP32_LIVE_READING.turbidity} NTU
                    </div>
                  </div>
                  <div>
                    <div className="label">Conductivity</div>
                    <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
                      {ESP32_LIVE_READING.conductivity} µS/cm
                    </div>
                  </div>
                  <div>
                    <div className="label">TDS</div>
                    <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
                      {ESP32_LIVE_READING.tds} ppm
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <div
                className="text-center text-muted"
                style={{ padding: "40px 0" }}
              >
                Click "Extract ESP32" to fetch sensor data
              </div>
            )}
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};
