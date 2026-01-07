import React, { createContext, useContext, useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("slim_token"));
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Extract token from URL on OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlToken = params.get("token");

    if (urlToken) {
      localStorage.setItem("slim_token", urlToken);
      setToken(urlToken);
      // Clean URL by removing token param
      window.history.replaceState({}, "", location.pathname);
    }
  }, [location]);

  // Dynamic API URL for production vs dev
  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Fetch user info when token changes
  useEffect(() => {
    const fetchUser = async () => {
      if (!token) {
        setLoading(false);
        return;
      }

      // Handle dev-token for access token login (bypass API call)
      if (token === "dev-token") {
        setUser({
          uid: "dev-user",
          email: "admin@slim.ai",
          name: "Admin User",
          role: "admin",
        });
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          // Token invalid, clear it
          localStorage.removeItem("slim_token");
          setToken(null);
          setUser(null);
        }
      } catch (error) {
        console.error("Auth check failed:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [token]);

  const login = () => {
    window.location.href = `${API_BASE_URL}/auth/login`;
  };

  // Login with access token (for dev/password login)
  const loginWithToken = (newToken) => {
    localStorage.setItem("slim_token", newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem("slim_token");
    localStorage.removeItem("slim_api_key");
    setToken(null);
    setUser(null);
    navigate("/login");
  };

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated,
        login,
        loginWithToken,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
