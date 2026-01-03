# Smart Lake Intelligence and Monitoring (SLIM AI)

## Overview
Urban and metro lakes across India face severe contamination from sewage inflow, industrial discharge, and runoff. Manual or delayed monitoring leaves pollution bursts undetected for hours or days, resulting in fish kills, health hazards, and ecosystem decline. SLIM AI delivers a real-time, scalable, and predictive lake-health monitoring platform that enables authorities to act before visible damage occurs.

## Problem Statement
- **No real-time monitoring:** Pollution surges can go unnoticed for extended periods.
- **Slow response:** Issues like fish kills, sewage inflow, or toxic blooms are detected only after damage occurs.
- **Low scalability:** Existing approaches are costly and difficult to expand across multiple lakes.
- **Reactive management:** Intervention typically happens only after visible signs of contamination.
- **No prediction:** Current solutions rarely forecast future risks or anomalies.

## SLIM AI Solution
SLIM AI continuously tracks key underwater parameters and provides instant insights to decision-makers.

### Core Capabilities
- **Real-time monitoring:** Continuous measurement of pH, turbidity, and temperature.
- **Anomaly detection:** Immediate identification of deviations that signal pollution events.
- **Live heatmap visualization:** Intuitive maps that highlight lake health zones and problem areas.
- **Instant alerts & secure logging:** Immediate notifications with tamper-resistant event storage.

### Innovation
SLIM AI unifies IoT sensing, machine-learning-driven prediction, and blockchain-backed data integrity in a single system. A tri-layer analytics architecture evaluates water quality in real time to deliver high accuracy and reliability.

### Unique Selling Points
| USP Parameter       | Existing Solutions                     | SLIM AI                              |
| ------------------- | -------------------------------------- | ------------------------------------ |
| Data predictiveness | Limited statistical trend analysis     | Machine-learning-based prediction    |
| Pollutant insight   | Reactive only when visible             | Proactive detection and forecasting  |
| Accuracy            | Moderate                               | High accuracy with tri-layer checks  |
| Transmission mode   | Physical (higher risk of data issues)  | Wireless and resilient               |

## How It Works
1. **IoT sensing:** Deployed sensors capture pH, turbidity, and temperature data continuously.
2. **Edge screening:** Early filters flag sudden spikes or drops for rapid attention.
3. **Cloud analytics:** ML models refine anomaly detection and generate short-term risk predictions.
4. **Visualization & alerts:** Live heatmaps and instant notifications guide swift, informed responses.

## Outcomes
- Faster detection and response to pollution events.
- Scalable coverage across many lakes without prohibitive costs.
- Predictive insights that reduce ecological and public health risks.
- Auditable, trustworthy data for regulators and stakeholders.

---

## FastAPI + Firebase backend
The `backend/` folder contains a FastAPI service that ingests sensor readings and stores them in Firebase Firestore.

### Project structure
```
backend/
  main.py                # FastAPI application with ingestion + analytics endpoints
  firebase_client.py     # Firestore client initialization
  ai_utils.py            # Gemini integration (gemini-2.5-flash-preview-09-2025)
  requirements.txt       # Python dependencies
  .env                   # Project configuration
```

### Environment variables
Set the following in your `.env` file:
- `FIREBASE_PROJECT_ID` – your Firebase project ID
- `FIREBASE_SERVICE_ACCOUNT_PATH` – path to `firebase-key.json`
- `GEMINI_API_KEY` – Google Gemini API key
- `API_SECRET_KEY` – shared secret for `x-api-key` header

### Running the backend
1. **Setup Firebase:** Follow `FIREBASE_SETUP_GUIDE.md` to get your `firebase-key.json`.
2. **Install and start the API:**
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Once running, the interactive API docs are at `http://localhost:8000/docs`.

### API endpoints
- `POST /api/lake-data` – ingest a reading (validated by `x-api-key`)
- `GET /api/lake-data/latest` – fetch the most recent reading from Firestore
- `GET /api/lake-data/history` – fetch reading history from Firestore
- `POST /api/data-query` – natural-language data analysis via Gemini 2.5 Flash
- `GET /api/research-models` – advanced GNN and causal analysis
- `GET /api/relationships` – sensor correlation and lag analysis
- `GET /api/tsf` – time-series forecasting insights

### Visualizing readings
An interactive dashboard script is available in `backend/visualize.py`. Use it to generate HTML reports from historical data.
