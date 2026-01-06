/**
 * SLIM AI Shared Components
 * Navigation, header, and common UI elements
 */

// Shared navigation HTML template
function createNavigation(activePage) {
  const pages = [
    {
      id: "dashboard",
      label: "Dashboard",
      href: "dashboard.html",
      icon: "grid",
    },
    {
      id: "prediction",
      label: "Prediction",
      href: "prediction.html",
      icon: "trending",
    },
    {
      id: "anomaly",
      label: "Anomaly",
      href: "anomaly.html",
      icon: "alert-triangle",
    },
    {
      id: "alerts",
      label: "Alerts",
      href: "alerts.html",
      icon: "bell",
      badge: null,
    },
    {
      id: "research",
      label: "Research",
      href: "research.html",
      icon: "search",
    },
    {
      id: "simulation",
      label: "Simulation",
      href: "simulation.html",
      icon: "play",
    },
    { id: "query", label: "Query", href: "query.html", icon: "message-circle" },
  ];

  const icons = {
    grid: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`,
    trending: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
    "alert-triangle": `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    bell: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>`,
    search: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    play: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
    "message-circle": `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/></svg>`,
  };

  const navLinks = pages
    .map((page) => {
      const isActive = page.id === activePage;
      const badge = page.badge
        ? `<span class="badge">${page.badge}</span>`
        : "";
      return `
      <li>
        <a href="${page.href}" class="nav-link ${isActive ? "active" : ""}">
          ${icons[page.icon] || ""}
          <span>${page.label}</span>
          ${badge}
        </a>
      </li>
    `;
    })
    .join("");

  return `
    <aside class="app-sidebar">
      <div class="sidebar-header">
        <span>SLIM</span> AI
      </div>
      
      <nav class="sidebar-nav">
        ${navLinks}
      </nav>
      
      <div class="sidebar-footer">
        <button class="btn btn-secondary" style="width: 100%; justify-content: flex-start;" onclick="logout()">
          <span style="margin-right: 8px;">←</span> Log out
        </button>
      </div>
    </aside>
  `;
}

// System status bar component
function createSystemStatusBar(options = {}) {
  const {
    status = "online",
    lastUpdate = "Just now",
    sensorsActive = 6,
    sensorsTotal = 6,
    alertsCount = 0,
  } = options;

  const statusText = {
    online: "All Systems Operational",
    degraded: "Degraded Performance",
    offline: "System Offline",
  };

  return `
    <div class="system-status-bar">
      <div class="system-status-left">
        <div class="system-status-indicator ${status}">
          <span class="status-dot"></span>
          <span>${statusText[status] || statusText.online}</span>
        </div>
        <span class="data-freshness">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          Last update: ${lastUpdate}
        </span>
      </div>
      <div class="system-status-right">
        <span>Sensors: ${sensorsActive}/${sensorsTotal} active</span>
        ${
          alertsCount > 0
            ? `<span style="color: var(--status-poor);">⚠ ${alertsCount} active alerts</span>`
            : ""
        }
      </div>
    </div>
  `;
}

// Metric card component
function createMetricCard(options) {
  const {
    label,
    value,
    unit,
    trend,
    trendValue,
    paramType, // ph, turbidity, temperature, do
    sparklineId,
  } = options;

  const trendClass =
    trend === "up" ? "up" : trend === "down" ? "down" : "stable";
  const trendIcon = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";

  return `
    <div class="metric-card highlight-${paramType}">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}<span class="metric-unit">${unit}</span></div>
      <div class="metric-trend ${trendClass}">
        <span>${trendIcon} ${trendValue}</span>
      </div>
      ${
        sparklineId
          ? `<div class="metric-sparkline" id="${sparklineId}"></div>`
          : ""
      }
    </div>
  `;
}

// Alert item component
function createAlertItem(options) {
  const {
    severity, // critical, warning, info
    title,
    location,
    time,
    duration,
    onInvestigate,
    onAcknowledge,
  } = options;

  return `
    <div class="alert-item ${severity}">
      <div class="alert-severity ${severity}"></div>
      <div class="alert-content">
        <div class="alert-title">${title}</div>
        <div class="alert-meta">${location} • ${time}${
    duration ? ` • Duration: ${duration}` : ""
  }</div>
      </div>
      <div class="alert-actions">
        <button class="btn btn-sm btn-secondary" onclick="${
          onInvestigate || ""
        }">Investigate</button>
        <button class="btn btn-sm btn-ghost" onclick="${
          onAcknowledge || ""
        }">Acknowledge</button>
      </div>
    </div>
  `;
}

// Initialize page with navigation
function initPage(activePage) {
  // Insert navigation
  const navContainer = document.getElementById("app-nav");
  if (navContainer) {
    navContainer.innerHTML = createNavigation(activePage);
  }

  // Auth check
  const AUTH_KEY = "slim_auth_token";
  const token = localStorage.getItem(AUTH_KEY);

  if (!token && !window.location.pathname.endsWith("login.html")) {
    window.location.href = "login.html";
    return false;
  }

  return true;
}

// Logout function
function logout() {
  localStorage.removeItem("slim_auth_token");
  window.location.href = "login.html";
}

// Format relative time
function formatRelativeTime(date) {
  const now = new Date();
  const diff = Math.floor((now - new Date(date)) / 1000);

  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    createNavigation,
    createSystemStatusBar,
    createMetricCard,
    createAlertItem,
    initPage,
    logout,
    formatRelativeTime,
  };
}
