import React, { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Badge } from "../ui";

// Fix Leaflet Icon Issue in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// Custom Buoy Icon
const getBuoyIcon = (status, selected) => {
  const color = status === "healthy" ? "#10b981" : "#f59e0b";
  const size = selected ? 18 : 14;

  return L.divIcon({
    className: "custom-buoy-icon",
    html: `<div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${color};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      transition: transform 0.2s;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -10],
  });
};

const MapController = ({ center }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, map.getZoom());
  }, [center, map]);
  return null;
};

export const LakeMap = ({ sensors, selectedId, onSelect }) => {
  const [center, setCenter] = useState([12.9825, 77.619]);

  // Ulsoor Lake Boundary (Mock)
  const lakeBoundary = [
    [12.9855, 77.618],
    [12.985, 77.62],
    [12.9842, 77.621],
    [12.9828, 77.6212],
    [12.9815, 77.6205],
    [12.9808, 77.619],
    [12.981, 77.6175],
    [12.9822, 77.6165],
    [12.9838, 77.6165],
    [12.9852, 77.6172],
    [12.9855, 77.618],
  ];

  return (
    <div style={{ height: "100%", width: "100%", position: "relative" }}>
      <MapContainer
        center={center}
        zoom={16}
        style={{ height: "100%", width: "100%", background: "#f8fafc" }}
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />

        <Polygon
          positions={lakeBoundary}
          pathOptions={{
            color: "#3b82f6",
            weight: 2,
            fillOpacity: 0.1,
            fillColor: "#3b82f6",
          }}
        />

        {sensors.map((s) => (
          <Marker
            key={s.id}
            position={[s.lat, s.lng]}
            icon={getBuoyIcon(s.status, selectedId === s.id)}
            eventHandlers={{
              click: () => onSelect(s.id),
            }}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={1}>
              {s.name}
            </Tooltip>
            {selectedId === s.id && (
              <Popup closeButton={false} autoPan={false}>
                <div style={{ textAlign: "center" }}>
                  <strong>{s.id}</strong>
                  <br />
                  {s.status}
                </div>
              </Popup>
            )}
          </Marker>
        ))}

        <MapController center={center} />
      </MapContainer>

      {/* Overlay Controls */}
      <div
        style={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        <button
          className="btn btn-sm btn-secondary"
          style={{ width: 32, height: 32, padding: 0 }}
          onClick={() => setCenter([12.9825, 77.619])}
        >
          ⌂
        </button>
      </div>
    </div>
  );
};
