"""Time-series forecasting utilities for hackathon-ready insights."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

CSV_FILE = Path(__file__).resolve().parent / "sample_lake_readings.csv"


def _load_frame() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["time_idx"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() / 3600
    return df


def _step_hours(df: pd.DataFrame) -> int:
    diffs = df["timestamp"].diff().dt.total_seconds().dropna()
    if diffs.empty:
        return 3
    return max(1, int(round(diffs.mode().iloc[0] / 3600)))


@dataclass
class _LinearForecast:
    next_value: float
    slope_per_hour: float


def _linear_forecast(series: pd.Series, hours: pd.Series, step_hours: int, steps: int = 1) -> _LinearForecast:
    if len(series) < 2:
        last_value = float(series.iloc[-1]) if not series.empty else 0.0
        return _LinearForecast(next_value=last_value, slope_per_hour=0.0)

    coef = np.polyfit(hours, series, deg=1)
    slope, intercept = coef
    future_hour = hours.iloc[-1] + step_hours * steps
    prediction = slope * future_hour + intercept
    return _LinearForecast(next_value=float(prediction), slope_per_hour=float(slope))


class TSFMetricForecast(BaseModel):
    metric: str
    horizon_hours: int
    value: float
    rationale: str


class SeasonalPatternForecast(BaseModel):
    label: str
    expected_value: float
    rationale: str


class HealthIndexForecast(BaseModel):
    next_value: float
    trend: str
    rationale: str


class TSFForecastResponse(BaseModel):
    ph_forecast: TSFMetricForecast
    do_forecast: TSFMetricForecast
    turbidity_pattern: SeasonalPatternForecast
    temperature_spike: SeasonalPatternForecast
    health_index: HealthIndexForecast


def _health_index(df: pd.DataFrame) -> pd.Series:
    def _safe_range(series: pd.Series) -> float:
        spread = series.max() - series.min()
        return spread if spread != 0 else 1.0

    ph_score = 1 - (df["ph"] - 7).abs() / 3  # closeness to neutral
    turbidity_score = 1 - (df["turbidity"] - df["turbidity"].min()) / _safe_range(
        df["turbidity"]
    )
    do_score = (df["do_level"] - df["do_level"].min()) / _safe_range(df["do_level"])
    temp_score = 1 - (df["temperature"] - df["temperature"].min()) / _safe_range(
        df["temperature"]
    )
    composite = (ph_score + turbidity_score + do_score + temp_score) / 4
    return composite.clip(lower=0, upper=1)


def compute_tsf_forecast() -> TSFForecastResponse:
    df = _load_frame()
    step_hours = _step_hours(df)
    hours = df["time_idx"]

    ph_linear = _linear_forecast(df["ph"], hours, step_hours)
    do_linear = _linear_forecast(df["do_level"], hours, step_hours, steps=2)

    next_timestamp = df["timestamp"].max() + pd.Timedelta(hours=step_hours)
    next_month = next_timestamp.month

    monthly_turbidity = df.assign(month=df["timestamp"].dt.month).groupby("month")["turbidity"].mean()
    expected_turbidity = float(monthly_turbidity.get(next_month, monthly_turbidity.mean()))
    turbidity_rationale = (
        f"Projected using month-average turbidity; next month {next_month} sits near {expected_turbidity:.1f} NTU"
    )

    summer_months = [6, 7, 8, 9]
    summer_slice = df[df["timestamp"].dt.month.isin(summer_months)]
    spike_value = float(summer_slice["temperature"].quantile(0.9) if not summer_slice.empty else df["temperature"].max())
    spike_rationale = "90th percentile of historical summer temperatures"

    health_series = _health_index(df)
    health_linear = _linear_forecast(health_series, hours, step_hours)
    trend = "rising" if health_linear.slope_per_hour > 0 else "softening"
    health_rationale = (
        f"Composite health index built from pH neutrality, low turbidity, high DO, and stable temps shows a {trend} trend"
    )

    ph_rationale = (
        f"Linear drift of {ph_linear.slope_per_hour:+.3f} pH/hour based on historical trajectory"
    )
    do_rationale = (
        f"Two-step projection with slope {do_linear.slope_per_hour:+.2f} DO/hour highlights depletion risk"
    )

    return TSFForecastResponse(
        ph_forecast=TSFMetricForecast(
            metric="ph",
            horizon_hours=step_hours,
            value=ph_linear.next_value,
            rationale=ph_rationale,
        ),
        do_forecast=TSFMetricForecast(
            metric="do_level",
            horizon_hours=step_hours * 2,
            value=do_linear.next_value,
            rationale=do_rationale,
        ),
        turbidity_pattern=SeasonalPatternForecast(
            label="seasonal_turbidity",
            expected_value=expected_turbidity,
            rationale=turbidity_rationale,
        ),
        temperature_spike=SeasonalPatternForecast(
            label="summer_temperature_spike",
            expected_value=spike_value,
            rationale=spike_rationale,
        ),
        health_index=HealthIndexForecast(
            next_value=float(health_linear.next_value),
            trend=trend,
            rationale=health_rationale,
        ),
    )
