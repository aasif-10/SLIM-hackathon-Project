import React, { useEffect, useState } from "react";
import { Sun, Moon, LogOut } from "lucide-react";
import { Button } from "../ui";
import { useAuth } from "../../context/AuthContext";
import "./layout.css";

export const TopBar = ({ title = "Dashboard" }) => {
  const { user, logout } = useAuth();
  const [theme, setTheme] = useState("light");

  // Initialize theme from local storage or default
  useEffect(() => {
    const savedTheme = localStorage.getItem("slim-theme") || "light";
    setTheme(savedTheme);
    document.documentElement.setAttribute("data-theme", savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("slim-theme", newTheme);
  };

  // Get user display name and avatar initial
  const displayName = user?.name || "User";
  const avatarInitial = displayName.charAt(0).toUpperCase();
  const avatarUrl = user?.picture;

  return (
    <header className="top-bar">
      <h1 className="page-title">{title}</h1>

      <div className="top-bar-actions">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          aria-label="Toggle Theme"
          className="theme-toggle"
        >
          {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
        </Button>

        <div className="user-profile">
          {avatarUrl ? (
            <img src={avatarUrl} alt={displayName} className="avatar-img" />
          ) : (
            <div className="avatar">{avatarInitial}</div>
          )}
          <span className="username">{displayName}</span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          aria-label="Logout"
          title="Sign out"
          style={{ marginLeft: "8px", color: "var(--text-muted)" }}
        >
          <LogOut size={18} />
        </Button>
      </div>
    </header>
  );
};
