/**
 * SLIM AI Authentication Guard
 * Handles token storage, verification, and redirection.
 */

const AUTH_KEY = "slim_auth_token";
const LOGIN_PAGE = "/login.html"; // Adjust if your structure is different, e.g. /frontend/login.html

// 1. Check if we are on the login page to avoid infinite loops
const isLoginPage = window.location.pathname.endsWith("login.html");

// 2. Parse Token from URL (Callback Handling)
const urlParams = new URLSearchParams(window.location.search);
const tokenFromUrl = urlParams.get("token");

if (tokenFromUrl) {
  console.log("[Auth] Token received from backend.");
  localStorage.setItem(AUTH_KEY, tokenFromUrl);
  // Clean URL
  const newUrl =
    window.location.protocol +
    "//" +
    window.location.host +
    window.location.pathname;
  window.history.replaceState({ path: newUrl }, "", newUrl);

  // If on login page, go to index
  if (isLoginPage) {
    window.location.href = "index.html";
  }
}

// 3. Authorization Check
const token = localStorage.getItem(AUTH_KEY);

if (!token && !isLoginPage) {
  console.warn("[Auth] No token found. Redirecting to login.");
  // Redirect to login page
  // Note: We need to handle the relative path correctly depending on how this is served
  // For now assuming the standard file structure

  // Static files are served from root, so just use relative path
  window.location.href = "login.html";
}

// 4. Logout Helper
window.logout = function () {
  localStorage.removeItem(AUTH_KEY);
  window.location.href = isLoginPage ? "#" : "login.html";
};

// 5. Expose wrapper for fetching protected data
window.authFetch = async function (url, options = {}) {
  const storedToken = localStorage.getItem(AUTH_KEY);
  if (!storedToken) {
    window.location.href = "login.html";
    return;
  }

  const headers = options.headers || {};
  headers["Authorization"] = `Bearer ${storedToken}`;

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401 || response.status === 403) {
    console.error("[Auth] Token invalid or expired.");
    localStorage.removeItem(AUTH_KEY);
    window.location.href = "login.html";
  }

  return response;
};
