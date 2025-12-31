import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import torch
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
from groq import Groq
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pytorch_forecasting import TimeSeriesDataSet
from pytorch_forecasting.models import TemporalFusionTransformer
from supabase_client import SupabaseConfigError, get_supabase
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


load_dotenv()
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_base_dataframe() -> pd.DataFrame:
    """Load and normalize lake readings from the local CSV."""
    data_path = Path(__file__).resolve().parent / "sample_lake_readings.csv"
    if not data_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data source not found at {data_path}",
        )

    df = pd.read_csv(data_path)

    if "timestamp" not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSV is missing the 'timestamp' column",
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["series_id"] = "buoy_1"
    df["time_idx"] = (
        (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() // 3600
    ).astype(int)

    for column in TARGETS:
        if column not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Column '{column}' missing from CSV",
            )
        df[column] = df[column].interpolate().bfill().ffill()

    return df


def _format_dataset_summary(df: pd.DataFrame) -> str:
    """Create a compact textual summary of the lake dataset for LLM prompts."""

    stats = []
    for col in TARGETS:
        col_data = df[col]
        stats.append(
            f"{col}: min={col_data.min():.2f}, max={col_data.max():.2f}, "
            f"mean={col_data.mean():.2f}, latest={col_data.iloc[-1]:.2f}"
        )

    latest_ts = df["timestamp"].iloc[-1].isoformat()
    return (
        "Dataset summary for lake readings. "
        f"Rows: {len(df)}; Time range: {df['timestamp'].min().isoformat()} to {latest_ts}. "
        f"Columns: {', '.join(TARGETS)}. "
        "Recent statistics: " + "; ".join(stats)
    )


def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GROQ_API_KEY is not configured on the server",
        )
    return Groq(api_key=api_key)


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
        supabase = get_supabase()
    except SupabaseConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    response = supabase.table("lake_readings").insert(reading.model_dump()).execute()

    if getattr(response, "error", None):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(response.error),
        )

    return {"message": "Data received", "id": response.data[0].get("id")}


@app.get("/api/lake-data/latest", response_model=LakeReadingResponse)
def fetch_latest_reading():
    try:
        supabase = get_supabase()
    except SupabaseConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    response = (
        supabase.table("lake_readings")
        .select("id,timestamp,ph,turbidity,temperature,do_level")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    if getattr(response, "error", None):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(response.error),
        )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No readings available",
        )

    return response.data[0]


@app.get("/api/lake-data/history", response_model=List[LakeReadingResponse])
def fetch_reading_history(limit: int = Query(100, gt=0, le=500)):
    try:
        supabase = get_supabase()
    except SupabaseConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    response = (
        supabase.table("lake_readings")
        .select("id,timestamp,ph,turbidity,temperature,do_level")
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    if getattr(response, "error", None):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(response.error),
        )
    return response.data


@app.get("/forecast/all", response_model=ForecastResponse)
def forecast_all():
    """Forecast lake parameters using TFT models stored in artifacts/."""
    base_df = _load_base_dataframe()
    return _generate_forecast(base_df)


@app.post("/api/analyze", response_model=FullAnomalyResponse)
def analyze_lake_data(
    reading: LakeInput,
    _: None = Depends(verify_api_key),
):
    result = analyze_lake_reading(reading)

    try:
        supabase = get_supabase()
        row = anomaly_to_row(reading, result)
        supabase.table("anomaly_results").insert(row).execute()
    except Exception as e:
        print(f"[anomaly] Error saving to Supabase: {e}")

    return result


@app.get("/api/patterns", response_model=ClusterPatternsResponse)
def get_cluster_patterns(
    _: None = Depends(verify_api_key),
):
    """Return clustering, PCA, and seasonal pattern summaries."""
    try:
        supabase = get_supabase()
    except SupabaseConfigError:
        supabase = None

    return compute_cluster_patterns(supabase=supabase)


@app.get("/api/relationships", response_model=RelationshipAnalysisResponse)
def get_relationship_analysis(
    _: None = Depends(verify_api_key),
):
    """Summarize inter-sensor relationships and lagged effects."""

    return compute_relationship_insights()


@app.get("/api/research-models", response_model=ResearchModelResponse)
def get_research_models(_: None = Depends(verify_api_key)):
    """Advanced research-grade models: GNNs, causal effects, and evaluation."""

    return compute_research_models()


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


@app.post("/api/data-query", response_model=DataQueryResponse)
def query_lake_dataset(payload: DataQuery, _: None = Depends(verify_api_key)):
    """Answer natural language questions about the lake CSV using Groq LLM."""

    df = _load_base_dataframe()
    dataset_summary = _format_dataset_summary(df)
    client = _get_groq_client()

    prompt = (
        "You are an assistant helping with lake sensor analytics. "
        "Use the provided dataset summary to answer the user's question succinctly. "
        "If the question is unrelated to the data, politely say you can only answer "
        "questions about the lake readings."
    )

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Dataset summary: {dataset_summary}\nQuestion: {payload.question}",
                },
            ],
            max_tokens=300,
            temperature=0.2,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq request failed: {exc}",
        )

    message = completion.choices[0].message.content if completion.choices else ""
    if not message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Received empty response from Groq",
        )

    return DataQueryResponse(answer=message)


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
