import os
from pathlib import Path
import traceback
from typing import Dict, List, Optional, Tuple

import pandas as pd
import torch
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pytorch_forecasting import TimeSeriesDataSet
from pytorch_forecasting.models import TemporalFusionTransformer
from firebase_client import get_firestore
from ai_utils import get_gemini_client
from anomaly import (
    LakeInput,
    FullAnomalyResponse,
    analyze_lake_reading,
    anomaly_to_row,   # <- add this if defined there
)

from clusters import ClusterPatternsResponse, compute_cluster_patterns
from relationships import RelationshipAnalysisResponse, compute_relationship_insights
from research_models import ResearchModelResponse, compute_research_models
from tsf import TSFForecastResponse, compute_tsf_forecast
from digital_twin import (
    DigitalTwinRequest,
    DigitalTwinResponse,
    simulate_digital_twin,
)
from event_detection import (
    EventDetectionRequest,
    EventDetectionResponse,
    detect_events,
)


load_dotenv(Path(__file__).resolve().parent.parent / ".env")
API_KEY_ENV_VAR = "API_SECRET_KEY"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
TARGETS = ["ph", "turbidity", "temperature", "do_level"]
READ_SENSOR_COMMAND = "read_sensor"
_pending_read_request: bool = False

_tft_models: Dict[str, TemporalFusionTransformer] = {}
_tft_datasets: Dict[str, TimeSeriesDataSet] = {}
_sanitized_ckpts: Dict[str, Path] = {}


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    expected_key = os.getenv(API_KEY_ENV_VAR)
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{API_KEY_ENV_VAR} is not configured on the server",
        )
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


class LakeReading(BaseModel):
    ph: float
    turbidity: float
    temperature: float
    do_level: float


class DataQuery(BaseModel):
    question: str = Field(..., description="Question about the lake readings CSV")


class DataQueryResponse(BaseModel):
    answer: str


class ForecastResponse(BaseModel):
    forecast_timestamp: str = Field(
        ...,
        description="ISO8601 timestamp for the next predicted interval",
    )
    predictions: LakeReading


class LakeReadingResponse(LakeReading):
    id: int
    timestamp: Optional[str]


app = FastAPI(
    title="SLIM AI Lake Data API",
    docs_url="/data",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "null"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "online", "message": "SLIM AI Lake Data API is running"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


def _load_base_dataframe() -> pd.DataFrame:
    """Load and normalize lake readings from Firestore, fallback to CSV if empty."""
    data_path = Path(__file__).resolve().parent / "sample_lake_readings.csv"
    
    try:
        db = get_firestore()
        docs = (
            db.collection("lake_readings")
            .order_by("timestamp", direction="DESCENDING")
            .limit(500)
            .stream()
        )
        data = [doc.to_dict() for doc in docs]
        if data:
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
            df["series_id"] = "buoy_1"
            df["time_idx"] = (
                (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() // 3600
            ).astype(int)
            for column in TARGETS:
                if column in df.columns:
                    df[column] = df[column].interpolate().bfill().ffill()
            return df
    except Exception as e:
        print(f"[main] Firestore load failed: {e}. Falling back to CSV.")

    if not data_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data source not found at {data_path}",
        )

    df = pd.read_csv(data_path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        df["series_id"] = "buoy_1"
        df["time_idx"] = (
            (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() // 3600
        ).astype(int)

    for column in TARGETS:
        if column in df.columns:
            df[column] = df[column].interpolate().bfill().ffill()

    return df


def _format_dataset_summary(df: pd.DataFrame) -> str:
    """Create a simple textual summary of the dataset for LLM prompts."""
    if df.empty:
        return "No sensor data available."

    stats = []
    available_cols = [c for c in TARGETS if c in df.columns]
    for col in available_cols:
        col_data = df[col]
        stats.append(
            f"{col}: min={col_data.min():.2f}, max={col_data.max():.2f}, "
            f"mean={col_data.mean():.2f}, latest={col_data.iloc[-1]:.2f}"
        )

    latest_ts = "unknown"
    if "timestamp" in df.columns:
        latest_ts = df["timestamp"].iloc[-1].isoformat()

    return f"Latest Reading Time: {latest_ts}\nSummary Statistics:\n" + "\n".join(stats)


# Consolidating Gemini setup via ai_utils


def _sanitize_checkpoint(target: str, ckpt_path: Path) -> Path:
    """Remove unsupported keys from a TFT checkpoint and cache the path."""
    if target in _sanitized_ckpts:
        return _sanitized_ckpts[target]

    checkpoint = torch.load(ckpt_path, map_location=torch.device("cpu"))
    hyper_parameters = checkpoint.get("hyper_parameters")

    if isinstance(hyper_parameters, dict) and "dataset" in hyper_parameters:
        sanitized_ckpt = ckpt_path.with_name(
            f"{ckpt_path.stem}_sanitized{ckpt_path.suffix}"
        )
        sanitized_hparams = dict(hyper_parameters)
        sanitized_hparams.pop("dataset", None)
        checkpoint["hyper_parameters"] = sanitized_hparams
        torch.save(checkpoint, sanitized_ckpt)
        _sanitized_ckpts[target] = sanitized_ckpt
    else:
        _sanitized_ckpts[target] = ckpt_path

    return _sanitized_ckpts[target]


def _load_tft_resources(
    target: str,
) -> Tuple[TemporalFusionTransformer, TimeSeriesDataSet]:
    """Load cached TFT model and dataset definition for a target column."""
    if target not in TARGETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown target '{target}'",
        )

    if target not in _tft_models or target not in _tft_datasets:
        ckpt_path = ARTIFACT_DIR / f"tft_{target}_best.ckpt"
        ds_path = ARTIFACT_DIR / f"tft_{target}_dataset.pkl"

        if not ckpt_path.exists() or not ds_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Missing artifacts for {target}. Expected {ckpt_path.name} "
                    f"and {ds_path.name} inside {ARTIFACT_DIR}."
                ),
            )

        dataset = TimeSeriesDataSet.load(str(ds_path))
        sanitized_ckpt = _sanitize_checkpoint(target, ckpt_path)
        model = TemporalFusionTransformer.load_from_checkpoint(
            checkpoint_path=str(sanitized_ckpt),
            map_location=torch.device("cpu"),
        )
        model.eval()

        _tft_datasets[target] = dataset
        _tft_models[target] = model

    return _tft_models[target], _tft_datasets[target]


def _determine_step_hours(df: pd.DataFrame) -> int:
    """Infer timestep spacing (in hours) from the dataset."""
    diffs = df["timestamp"].diff().dt.total_seconds().dropna()
    if diffs.empty:
        return 1
    mode_val = diffs.mode().iloc[0] if not diffs.mode().empty else 3600
    hours = max(1, int(round(mode_val / 3600)))
    return hours


def _prepare_prediction_frame(
    df: pd.DataFrame, prediction_length: int
) -> Tuple[pd.DataFrame, str]:
    """Append future rows so the TFT model can forecast the next window."""
    step_hours = _determine_step_hours(df)
    last_timestamp = df["timestamp"].max()
    last_idx = int(df["time_idx"].max())

    # last known sensor values
    last_values = df.iloc[-1][TARGETS]

    future_rows = []
    for horizon in range(1, prediction_length + 1):
        row = {
            "timestamp": last_timestamp + pd.Timedelta(hours=step_hours * horizon),
            "time_idx": last_idx + horizon,
            "series_id": "buoy_1",
        }
        # copy last known reading for all targets
        for col in TARGETS:
            row[col] = float(last_values[col])
        future_rows.append(row)

    future_df = pd.DataFrame(future_rows)
    combined = pd.concat([df, future_df], ignore_index=True)

    # safety: ensure no NaNs slipped in anywhere
    for col in TARGETS:
        combined[col] = combined[col].interpolate().bfill().ffill()

    forecast_timestamp = future_rows[0]["timestamp"].isoformat()
    return combined, forecast_timestamp


def _generate_forecast(df: pd.DataFrame) -> ForecastResponse:
    """Run TFT models for each parameter and return the next-step forecast."""
    predictions: Dict[str, float] = {}
    forecast_timestamp: Optional[str] = None

    for target in TARGETS:
        model, dataset = _load_tft_resources(target)
        prediction_length = dataset.max_prediction_length
        prepared_df, candidate_ts = _prepare_prediction_frame(df, prediction_length)

        predict_ds = TimeSeriesDataSet.from_dataset(
            dataset,
            prepared_df,
            predict=True,
            stop_randomization=True,
        )
        predict_loader = predict_ds.to_dataloader(
            train=False, batch_size=64, num_workers=0
        )

        forecast_tensor = model.predict(predict_loader)
        if forecast_tensor.ndim == 3:
            # Take median quantile if quantile dimension is present
            forecast_tensor = forecast_tensor[..., forecast_tensor.shape[-1] // 2]
        next_value = float(forecast_tensor[0, 0].detach().cpu().item())

        predictions[target] = next_value
        forecast_timestamp = forecast_timestamp or candidate_ts

    return ForecastResponse(
        forecast_timestamp=forecast_timestamp,
        predictions=LakeReading(**predictions),
    )


@app.post("/api/lake-data", status_code=status.HTTP_201_CREATED)
def ingest_lake_data(
    reading: LakeReading,
    _: None = Depends(verify_api_key),
):
    try:
        db = get_firestore()
        # Firestore expects a dict, including a server timestamp if needed
        data = reading.model_dump()
        data["timestamp"] = pd.Timestamp.now().isoformat()
        _, doc_ref = db.collection("lake_readings").add(data)
        return {"message": "Data received", "id": doc_ref.id}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.get("/api/lake-data/latest", response_model=LakeReadingResponse)
def fetch_latest_reading():
    try:
        db = get_firestore()
        docs = (
            db.collection("lake_readings")
            .order_by("timestamp", direction="DESCENDING")
            .limit(1)
            .stream()
        )
        data = [doc.to_dict() for doc in docs]
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No readings available",
            )
        # Firestore doesn't provide an 'id' integer by default, so we use document ID
        res = data[0]
        res["id"] = 0  # Dummy ID for compatibility
        return res
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        print(f"[latest] Endpoint Error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.get("/api/lake-data/history", response_model=List[LakeReadingResponse])
def fetch_reading_history(limit: int = Query(100, gt=0, le=500)):
    try:
        db = get_firestore()
        docs = (
            db.collection("lake_readings")
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        results = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = 0  # Dummy ID
            results.append(d)
        return results
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        print(f"[history] Endpoint Error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.get("/forecast/all", response_model=ForecastResponse)
def forecast_all():
    """Forecast lake parameters using TFT models or a linear fallback."""
    try:
        if not ARTIFACT_DIR.exists():
            print("[forecast] ARTIFACT_DIR missing; using linear TSF fallback.")
            return _generate_fallback_forecast()
            
        base_df = _load_base_dataframe()
        return _generate_forecast(base_df)
    except Exception as exc:
        print(f"[{pd.Timestamp.now()}] Forecast Error: {traceback.format_exc()}")
        # Final fallback to linear TSF logic if even _generate_forecast fails
        try:
            return _generate_fallback_forecast()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Forecast Error: {str(exc)}",
            )


def _generate_fallback_forecast() -> ForecastResponse:
    """Uses linear/seasonal TSF logic as a fallback for the TFT forecast."""
    from tsf import compute_tsf_forecast
    tsf_data = compute_tsf_forecast()
    
    # Map TSF values to the ForecastResponse schema
    return ForecastResponse(
        forecast_timestamp=pd.Timestamp.now().isoformat(),
        predictions=LakeReading(
            ph=tsf_data.ph_forecast.value,
            turbidity=tsf_data.turbidity_pattern.expected_value,
            temperature=tsf_data.temperature_spike.expected_value,
            do_level=tsf_data.do_forecast.value
        )
    )


@app.post("/api/analyze", response_model=FullAnomalyResponse)
def analyze_lake_data(
    reading: LakeInput,
    _: None = Depends(verify_api_key),
):
    result = analyze_lake_reading(reading)

    try:
        db = get_firestore()
        row = anomaly_to_row(reading, result)
        db.collection("anomaly_results").add(row)
    except Exception as e:
        print(f"[anomaly] Error saving to Firebase: {e}")

    return result


@app.get("/api/patterns", response_model=ClusterPatternsResponse)
def get_cluster_patterns(
    _: None = Depends(verify_api_key),
):
    """Return clustering, PCA, and seasonal pattern summaries."""
    try:
        db = get_firestore()
    except Exception:
        db = None

    return compute_cluster_patterns(db=db)


@app.get("/api/relationships", response_model=RelationshipAnalysisResponse)
def get_relationship_analysis(
    _: None = Depends(verify_api_key),
):
    """Summarize inter-sensor relationships and lagged effects."""

    return compute_relationship_insights()


@app.get("/api/research-models", response_model=ResearchModelResponse)
def get_research_models(_: None = Depends(verify_api_key)):
    """Advanced research-grade models: GNNs, causal effects, and evaluation."""
    try:
        return compute_research_models()
    except Exception as e:
        print(f"[research-models] Endpoint Error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research Models Error: {str(e)}"
        )


@app.get("/api/tsf", response_model=TSFForecastResponse)
def get_tsf_forecasts(
    _: None = Depends(verify_api_key),
):
    """Deliver hackathon-friendly time-series forecasts for lake health."""

    return compute_tsf_forecast()


@app.post("/api/digital-twin", response_model=DigitalTwinResponse)
def simulate_digital_twin_route(
    payload: DigitalTwinRequest,
    _: None = Depends(verify_api_key),
):
    """Run digital-twin style what-if scenarios using the 1-year archive."""

    return simulate_digital_twin(payload)


@app.post("/api/event-detection", response_model=EventDetectionResponse)
def run_event_detection(
    payload: EventDetectionRequest,
    _: None = Depends(verify_api_key),
):
    """Detect label-free events like polluted inflow or aerator failure."""

    return detect_events(payload)


@app.post("/api/expert-analysis", response_model=DataQueryResponse)
def run_expert_lake_analysis(payload: DataQuery, _: None = Depends(verify_api_key)):
    """Deep ecological analysis of lake health using Gemini for broader reasoning."""
    df = _load_base_dataframe()
    dataset_summary = _format_dataset_summary(df)
    client = get_gemini_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured",
        )

    system_prompt = (
        "You are 'SLIM AI Senior Ecology Specialist'. Provide a highly concise, data-driven analysis.\n\n"
        "STRICT STRUCTURE:\n"
        "1. CONCLUSION: [Single bold sentence identifying the status/suitability]\n"
        "2. SCIENTIFIC REASONING: [3-4 short bullet points explaining the 'why' based on current data trends.]\n\n"
        "Rules: No introductions. No fluff. Be direct and technical."
    )

    try:
        prompt = f"{system_prompt}\n\nDATA:\n{dataset_summary}\n\nQUESTION: {payload.question}"
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-09-2025",
            contents=prompt,
            config={
                "max_output_tokens": 1000,
                "temperature": 0.2,
                "safety_settings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            },
        )
        if not response.text:
            print(f"[Expert] Empty response from Gemini. Candidates: {response.candidates}")
    except Exception as exc:
        print(f"[Expert] Generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Expert analysis engine failed: {exc}",
        )

    message = response.text if response.text else "The analysis engine could not generate a response due to safety filters or empty completion."
    return DataQueryResponse(answer=message)


@app.post("/api/data-query", response_model=DataQueryResponse)
def query_lake_dataset(payload: DataQuery, _: None = Depends(verify_api_key)):
    """Handle standard quick-data questions with simplified reasoning."""
    df = _load_base_dataframe()
    dataset_summary = _format_dataset_summary(df)
    client = get_gemini_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured",
        )

    system_prompt = (
        "You are a simple lake data assistant. Use the dataset summary to answer "
        "the question directly. Keep it brief."
    )

    try:
        prompt = f"{system_prompt}\n\nDATA: {dataset_summary}\nQUESTION: {payload.question}"
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-09-2025",
            contents=prompt,
            config={
                "max_output_tokens": 200,
                "temperature": 0.1,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Data query failed: {exc}",
        )

    return DataQueryResponse(answer=response.text if response.text else "No data found.")


class CommandResponse(BaseModel):
    command: str


@app.post("/api/esp32/request-read")
def request_esp32_read(_: None = Depends(verify_api_key)):
    """Signal the ESP32 to take one reading on its next poll."""

    global _pending_read_request
    _pending_read_request = True
    return {"message": "Sensor read requested"}


@app.get("/api/next-command", response_model=CommandResponse)
def get_next_command(_: None = Depends(verify_api_key)):
    """ESP32 polls this endpoint; returns a one-time read command when pending."""

    global _pending_read_request
    if _pending_read_request:
        _pending_read_request = False
        return CommandResponse(command=READ_SENSOR_COMMAND)

    return CommandResponse(command="idle")
