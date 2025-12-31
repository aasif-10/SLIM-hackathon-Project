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

## FastAPI + Supabase backend
The `backend/` folder contains a simple FastAPI service that ingests sensor readings from an ESP32 and stores them in a Supabase Postgres table.

### Project structure
```
backend/
  main.py                # FastAPI application with ingestion + query endpoints
  supabase_client.py     # Cached Supabase client helper
  requirements.txt       # Python dependencies
  .env.example           # Example environment variables
  migrations/
    create_lake_readings.sql  # Table definition for Supabase
```

### Environment variables
Copy `.env.example` to `.env` and set the values:
- `SUPABASE_URL` – your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` – service role key (required for inserts)
- `API_SECRET_KEY` – shared secret used to validate the `x-api-key` request header

### Running the backend
1. **Set environment variables:** Copy `.env.example` to `.env` and fill in your Supabase URL, service role key, and API secret key.
2. **Create the table:** Run the SQL in `backend/migrations/create_lake_readings.sql` against your Supabase database.
3. **Install and start the API:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000  # or: python main.py
```

Once running, the interactive API docs (Swagger UI) are available at `http://localhost:8000/docs` and ReDoc at `http://localhost:8000/redoc`.

### API endpoints
- `POST /api/lake-data` – ingest a reading after validating the `x-api-key` header
- `GET /api/lake-data/latest` – fetch the most recent reading
- `GET /api/lake-data/history?limit=100` – fetch the latest N readings (default 100, max 500)
- `POST /api/data-query` – answer natural-language questions about the lake CSV via the Groq LLM
- `POST /api/digital-twin` – simulate warming, pollution slug, and rainfall-driven turbidity recovery
- `POST /api/event-detection` – label-free event checks (polluted inflow, rain turbidity, aerator risk)

Example POST payload with header:
```bash
curl -X POST "http://localhost:8000/api/lake-data" \
  -H "Content-Type: application/json" \
  -H "x-api-key: MY_SECRET_KEY" \
  -d '{
        "ph": 7.2,
        "turbidity": 560,
        "temperature": 26.4,
        "do_level": 300
      }'
```

Sample Groq-backed query using the same API key:
```bash
curl -X POST "http://localhost:8000/api/data-query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: MY_SECRET_KEY" \
  -d '{
        "question": "What are the recent average turbidity levels and are they trending up?"
      }'
```

### Supabase table
Apply the SQL in `backend/migrations/create_lake_readings.sql` to create the `lake_readings` table:
```sql
CREATE TABLE lake_readings (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp timestamptz DEFAULT now(),
    ph float,
    turbidity float,
    temperature float,
    do_level float
);
```

### Notes
- CORS is enabled for all origins to simplify IoT testing.
- The Supabase client is cached to avoid re-initialization overhead.
- Requests fail fast with descriptive errors when the API key or Supabase configuration is missing.

### Visualizing a year's worth of readings
An interactive Plotly dashboard can be generated directly from the CSV archive (sample provided in `backend/sample_lake_readings.csv`). From the `backend/` directory run:

```bash
pip install -r requirements.txt  # ensures pandas + plotly are present
python visualize_lake_readings.py sample_lake_readings.csv --output lake_dashboard.html
```

Open the resulting `lake_dashboard.html` to explore:
- Stacked time series with daily rolling averages and a range slider.
- Diurnal temperature heatmap (hour vs. day of year).
- Monthly box plots for seasonal shifts.
- A quick correlation matrix across pH, turbidity, temperature, and DO.
