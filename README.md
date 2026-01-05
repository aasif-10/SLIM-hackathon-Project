# SLIM AI (Smart Lake Intelligence and Monitoring)

![Project Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-HTML5%20%2F%20JS-orange)

**SLIM AI** is a production-grade, real-time predictive analytics platform designed to safeguard urban water bodies. It transforms raw sensor flows into actionable ecological intelligence, enabling municipalities and environmental regulators to predict pollution events, monitor ecosystem health, and prevent ecological collapse.

## 🌍 Overview

Urban lakes are critical resilient infrastructure, yet they are increasingly threatened by untreated sewage influx, industrial dumping, and climate-driven stagnation. Traditional monitoring—manual sampling once a month—is too slow to catch acute pollution events.

**SLIM AI** solves this by providing a "digital nervous system" for the lake. It combines IoT sensing with advanced statistical ML to detect anomalies in real-time, simulate "what-if" recovery scenarios, and forecast water quality trends hours in advance.

## 🚀 Key capabilities

- **Real-time Anomaly Detection**: Uses `IsolationForest` and Z-score statistical envelopes to instantly flag sensor readings that deviate from the ecological baseline.
- **Label-Free Event Classification**: automatically distinguishes between:
  - Combined Sewer Overflows (CSO)
  - Illegal Industrial Dumping (Acid/Alkaline spikes)
  - Aerator Failures & Stagnation
  - Algae Bloom Onset Risks
- **Digital Twin Simulation**: A physics-aware projection engine that simulates the impact of rainfall, temperature spikes, or pollution loads on Dissolved Oxygen (DO) and turbidity recovery times.
- **Secure Ops**: Enterprise-grade Google OAuth 2.0 authentication and stateless JWT architecture ensuring secure access for officials and researchers.

## 🏗 System Architecture

The platform follows a modular, cloud-native architecture designed for horizontal scalability.

```mermaid
graph TD
    A[IoT Sensors (ESP32)] -->|HTTPS/JSON| B[Ingestion API (FastAPI)]
    B --> C[(Firestore NoSQL)]
    B --> D[Anomaly Engine (Isolation Forest)]
    B --> E[Event Detective (Heuristic Envelopes)]
    D & E --> F[Alerting Service]

    User[Researcher/Official] -->|OAuth 2.0| G[Frontend Dashboard]
    G -->|Query| B
    G -->|Simulate| H[Digital Twin Engine]
```

### 1. Ingestion Layer (`backend/`)

Built on **FastAPI**, providing high-throughput endpoints for sensor data. It handles validation, normalization, and persistent storage.

### 2. Analytics Layer

- **`anomaly.py`**: The watchdog. Runs every incoming reading against historical distributions to calculate severity scores.
- **`event_detection.py`**: The diagnostician. Evaluates multi-variate correlations (e.g., "Rising Temp" + "Dropping DO") to identify specific physical phenomena.
- **`tsf.py`**: The forecaster. Short-term trend projection using linear regression and seasonal decomposition.

### 3. Visualization Layer (`frontend/`)

A responsive, dark-mode dashboard providing:

- Live telemetry and historical trends.
- Geospatial sensor mapping.
- Interactive simulation controls for decision support.

## 🛡️ Security & Integrity

- **Identity**: All access is gated via Google OAuth 2.0.
- **Stateless**: No server-side sessions; fully JWT-based verification.
- **Audit**: Every anomaly decision is logged with a computed "Reasoning" string for explainability.

## 🏁 Getting Started

### Prerequisites

- Python 3.10+
- Google Cloud Credentials (for OAuth)
- Firebase Service Account

### Installation

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/your-org/slim-ai.git
    cd slim-ai
    ```

2.  **Environment Setup**
    Create a `.env` file in the root:

    ```env
    GOOGLE_CLIENT_ID=your_client_id
    GOOGLE_CLIENT_SECRET=your_client_secret
    SECRET_KEY=your_jwt_secret
    BASE_URL=http://localhost:8000
    ```

3.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Platform**
    ```bash
    uvicorn backend.main:app --reload
    ```
    Access the dashboard at `http://localhost:8000/`.

## 🔮 Future Roadmap

- **Computer Vision**: Integration of drone-based hyperspectral imaging for bloom extent mapping.
- **LoRaWAN Support**: Low-power wide-area network support for remote buoys without cellular coverage.
- **Blockchain Audit**: Hashing sensor records to a ledger for tamper-proof regulatory compliance.

## 🤝 Contributing

We welcome contributions from hydrologists, data scientists, and engineers. Please read `CONTRIBUTING.md` for our code of conduct and pull request standards.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
