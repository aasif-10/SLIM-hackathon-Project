import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutGrid,
  TrendingUp,
  AlertTriangle,
  Bell,
  Search,
  Play,
  MessageCircle,
  Mic,
  LogOut,
} from "lucide-react";
import clsx from "clsx";
import { useAuth } from "../../context/AuthContext";
import "./layout.css";

const NAV_ITEMS = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { path: "/prediction", label: "Prediction", icon: TrendingUp },
  { path: "/anomaly", label: "Anomaly", icon: AlertTriangle },
  { path: "/alerts", label: "Alerts", icon: Bell },
  { path: "/research", label: "Research", icon: Search },
  { path: "/simulation", label: "Simulation", icon: Play },
  { path: "/query", label: "Query", icon: MessageCircle },
  { path: "/voice-agent", label: "Voice Agent", icon: Mic },
];

export const Sidebar = () => {
  const { logout } = useAuth();
  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <span className="brand-logo">SLIM</span> AI
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => clsx("nav-link", isActive && "active")}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="nav-link logout-btn" onClick={logout}>
          <LogOut size={18} />
          <span>Log Out</span>
        </button>
      </div>
    </aside>
  );
};
