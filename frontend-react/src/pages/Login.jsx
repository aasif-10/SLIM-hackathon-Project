import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Card, Button, Input } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import "../styles/theme.css"; // ensure vars are avail

const GoogleIcon = () => (
  <svg style={{ width: 18, height: 18 }} viewBox="0 0 24 24">
    <path
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      fill="#4285F4"
    />
    <path
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      fill="#34A853"
    />
    <path
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      fill="#FBBC05"
    />
    <path
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      fill="#EA4335"
    />
  </svg>
);

export const Login = () => {
  const navigate = useNavigate();
  const { isAuthenticated, login, loginWithToken } = useAuth();
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleLogin = () => {
    login();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Fake network delay simulation
    await new Promise((resolve) => setTimeout(resolve, 800));

    if (apiKey === "password") {
      localStorage.setItem("slim_api_key", apiKey);
      loginWithToken("dev-token");
      // Navigation handled by useEffect when isAuthenticated changes
    } else {
      setError("Invalid system credentials");
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        backgroundColor: "var(--bg-body)",
      }}
    >
      <Card
        style={{
          width: "100%",
          maxWidth: 420,
          padding: 40,
          textAlign: "center",
        }}
      >
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
        >
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--primary)",
              marginBottom: 8,
            }}
          >
            SLIM AI
          </h1>
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              marginBottom: 32,
            }}
          >
            Smart Lake Intelligence & Monitoring
          </p>
        </motion.div>

        <div style={{ marginBottom: 24 }}>
          <Button
            variant="secondary"
            onClick={handleGoogleLogin}
            style={{ width: "100%" }}
          >
            <GoogleIcon />
            Sign in with Google
          </Button>
        </div>

        <div
          style={{ display: "flex", alignItems: "center", marginBottom: 24 }}
        >
          <div
            style={{ flex: 1, height: 1, background: "var(--border-color)" }}
          />
          <span
            style={{
              padding: "0 12px",
              fontSize: "0.8rem",
              color: "var(--text-muted)",
            }}
          >
            or use access token
          </span>
          <div
            style={{ flex: 1, height: 1, background: "var(--border-color)" }}
          />
        </div>

        <form onSubmit={handleSubmit}>
          <Input
            label="Access Token"
            type="password"
            placeholder="Enter system key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            error={error}
            disabled={loading}
          />
          <Button
            type="submit"
            variant="primary"
            style={{ width: "100%", marginTop: 8 }}
            disabled={loading}
          >
            {loading ? "Verifying..." : "Access Dashboard"}
          </Button>
        </form>

        <div
          style={{
            marginTop: 32,
            fontSize: "0.75rem",
            color: "var(--text-muted)",
          }}
        >
          &copy; 2026 SLIM AI System v3.1 (React)
        </div>
      </Card>
    </div>
  );
};
