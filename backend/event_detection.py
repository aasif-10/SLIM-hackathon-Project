"""Label-free event detection helpers built on statistical envelopes + heuristics."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

CSV_FILE = Path(__file__).resolve().parent / "sample_lake_readings.csv"


def _load_df() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


df = _load_df()

PH_MEAN, PH_STD = float(df["ph"].mean()), float(df["ph"].std())
TURB_MEAN, TURB_STD = float(df["turbidity"].mean()), float(df["turbidity"].std())
TEMP_MEAN, TEMP_STD = float(df["temperature"].mean()), float(df["temperature"].std())
DO_MEAN, DO_STD = float(df["do_level"].mean()), float(df["do_level"].std())

DAY_DO = float(df[df["timestamp"].dt.hour.between(6, 18)]["do_level"].mean())
NIGHT_DO = float(df[~df["timestamp"].dt.hour.between(6, 18)]["do_level"].mean())
DIURNAL_DELTA = DAY_DO - NIGHT_DO


@dataclass
class EventSignal:
    name: str
    triggered: bool
    severity: str
    reason: str


class EventDetectionReading(BaseModel):
    ph: float
    turbidity: float
    temperature: float
    do_level: float


class EventDetectionRequest(BaseModel):
    reading: EventDetectionReading
    previous_readings: Optional[List[EventDetectionReading]] = Field(
        None,
        description="Optional history (oldest->newest) to learn drifts/trends",
    )
    rainfall_mm: float = Field(0, description="Recent rainfall depth in millimeters")
    measurement_hour: Optional[int] = Field(
        None, ge=0, le=23, description="Hour-of-day for diurnal checks"
    )


class EventFlag(BaseModel):
    name: str
    triggered: bool
    severity: str
    reason: str


class EventDetectionResponse(BaseModel):
    flags: List[EventFlag]
    summary: List[str]


def _trend_slope(history: List[EventDetectionReading], attr: str) -> float:
    if len(history) < 2:
        return 0.0
    y = np.array([getattr(r, attr) for r in history], dtype=float)
    x = np.arange(len(history))
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)


def detect_events(payload: EventDetectionRequest) -> EventDetectionResponse:
    r = payload.reading
    history = payload.previous_readings or []
    flags: List[EventSignal] = []

    do_trend = _trend_slope(history[-5:], "do_level") if history else 0.0

    # Sudden polluted inflow
    polluted = (
        r.turbidity > TURB_MEAN + 2 * TURB_STD
        or r.ph < PH_MEAN - 2 * PH_STD
        or (history and r.turbidity - history[-1].turbidity > TURB_STD)
    )
    flags.append(
        EventSignal(
            name="Sudden polluted inflow",
            triggered=polluted,
            severity="high" if polluted else "none",
            reason=(
                "Turbidity/pH deviated sharply from baseline envelope"
                if polluted
                else "Within baseline dispersion"
            ),
        )
    )

    # Heavy rain effect on turbidity
    heavy_rain = payload.rainfall_mm >= 15 and r.turbidity > TURB_MEAN + TURB_STD
    flags.append(
        EventSignal(
            name="Heavy rain turbidity response",
            triggered=heavy_rain,
            severity="medium" if heavy_rain else "none",
            reason=(
                f"{payload.rainfall_mm} mm rain + elevated turbidity"
                if heavy_rain
                else "No rain-driven turbidity signature"
            ),
        )
    )

    # Aerator failure prediction
    aerator_fail = (
        r.do_level < DO_MEAN - 1.5 * DO_STD
        and r.temperature > TEMP_MEAN + 0.5 * TEMP_STD
    ) or (do_trend < -0.2 and r.do_level < DO_MEAN)
    flags.append(
        EventSignal(
            name="Aerator failure risk",
            triggered=aerator_fail,
            severity="high" if aerator_fail else "none",
            reason=(
                "DO slumping alongside warming column; probable aerator outage"
                if aerator_fail
                else "DO stable; no outage signature"
            ),
        )
    )

    # Sensor drift detection (monotonic creep without spikes)
    drift = False
    drift_reason = ""
    if history:
        temp_slope = _trend_slope(history[-6:], "temperature")
        ph_slope = _trend_slope(history[-6:], "ph")
        drift = (
            abs(temp_slope) < 0.2
            and abs(ph_slope) < 0.05
            and abs(r.temperature - history[0].temperature) > TEMP_STD * 0.5
        )
        if drift:
            drift_reason = "Slow monotonic offset suggests sensor drift"
    flags.append(
        EventSignal(
            name="Sensor drift",
            triggered=drift,
            severity="low" if drift else "none",
            reason=drift_reason or "No drift signature",
        )
    )

    # Sensor malfunction (impossible or frozen values)
    malfunction = (
        r.ph < 4
        or r.ph > 10
        or r.turbidity < 0
        or (history and all(getattr(history[0], f) == getattr(h, f) for h in history for f in ["ph", "turbidity", "temperature", "do_level"]))
    )
    flags.append(
        EventSignal(
            name="Sensor malfunction",
            triggered=malfunction,
            severity="high" if malfunction else "none",
            reason=(
                "Impossible chemistry or frozen sensor stream"
                if malfunction
                else "Values within physical range"
            ),
        )
    )

    # Night vs day chemistry cycle detection
    night_day_trigger = False
    cycle_reason = ""
    if payload.measurement_hour is not None:
        expected = NIGHT_DO if payload.measurement_hour < 6 or payload.measurement_hour >= 20 else DAY_DO
        deviation = r.do_level - expected
        night_day_trigger = abs(deviation) > abs(DIURNAL_DELTA) * 0.75
        cycle_reason = (
            f"DO deviated {deviation:.2f} mg/L from typical {'night' if payload.measurement_hour < 6 or payload.measurement_hour >= 20 else 'day'} level"
            if night_day_trigger
            else "Within expected diurnal band"
        )
    flags.append(
        EventSignal(
            name="Night vs day chemistry cycle",
            triggered=night_day_trigger,
            severity="medium" if night_day_trigger else "none",
            reason=cycle_reason or "Hour not provided",
        )
    )

    # Critical DO-driven fish mortality risk
    do_critical = r.do_level <= 3 or r.do_level < DO_MEAN - 2 * DO_STD
    fish_mortality = do_critical or (do_trend < -0.4 and r.do_level < DO_MEAN - DO_STD)
    flags.append(
        EventSignal(
            name="Fish mortality prediction",
            triggered=fish_mortality,
            severity="high" if fish_mortality else "none",
            reason=(
                "Critical dissolved oxygen collapse; fish kill likely"
                if fish_mortality
                else "DO within survivable band"
            ),
        )
    )

    # Explicit DO threshold alert
    do_below_three = r.do_level <= 3
    flags.append(
        EventSignal(
            name="DO < 3 mg/L",
            triggered=do_below_three,
            severity="high" if do_below_three else "none",
            reason=(
                "DO reading below 3 mg/L survival threshold"
                if do_below_three
                else "Above 3 mg/L"
            ),
        )
    )

    # Heat stress + low oxygen combined anomaly
    heat_low_do = (
        r.temperature > TEMP_MEAN + TEMP_STD
        and (r.do_level < DO_MEAN - DO_STD or do_critical)
    )
    flags.append(
        EventSignal(
            name="High temperature stress + low DO",
            triggered=heat_low_do,
            severity="high" if heat_low_do else "none",
            reason=(
                "Warming water with concurrent oxygen slump"
                if heat_low_do
                else "No combined heat/DO stress signature"
            ),
        )
    )

    # Algae bloom risk signals
    temp_bloom = r.temperature > TEMP_MEAN + 0.75 * TEMP_STD
    ph_bloom = r.ph > max(PH_MEAN + 0.8 * PH_STD, 8.3)
    do_bloom = r.do_level < DO_MEAN - 0.75 * DO_STD or do_trend < -0.3

    flags.append(
        EventSignal(
            name="Algae bloom - high temperature",
            triggered=temp_bloom,
            severity="medium" if temp_bloom else "none",
            reason=(
                "Thermally favorable conditions for bloom"
                if temp_bloom
                else "Temperature within normal band"
            ),
        )
    )
    flags.append(
        EventSignal(
            name="Algae bloom - high pH",
            triggered=ph_bloom,
            severity="medium" if ph_bloom else "none",
            reason=(
                "pH elevated into bloom-favoring range"
                if ph_bloom
                else "pH near baseline"
            ),
        )
    )
    flags.append(
        EventSignal(
            name="Algae bloom - low DO pattern",
            triggered=do_bloom,
            severity="medium" if do_bloom else "none",
            reason=(
                "Oxygen deficit consistent with bloom respiration"
                if do_bloom
                else "No bloom-driven DO depletion"
            ),
        )
    )

    multivariate_bloom = sum([temp_bloom, ph_bloom, do_bloom]) >= 2
    flags.append(
        EventSignal(
            name="Algae bloom - multivariate trigger",
            triggered=multivariate_bloom,
            severity="high" if multivariate_bloom else "none",
            reason=(
                "Multiple bloom drivers aligned (temp/pH/DO)"
                if multivariate_bloom
                else "No combined bloom signature"
            ),
        )
    )

    # Sediment disturbance or clogging
    turbidity_jump = (
        r.turbidity > TURB_MEAN + 2.5 * TURB_STD
        or (history and r.turbidity - history[-1].turbidity > 1.5 * TURB_STD)
    )
    flags.append(
        EventSignal(
            name="Clogging / sediment disturbance",
            triggered=turbidity_jump,
            severity="medium" if turbidity_jump else "none",
            reason=(
                "Sudden turbidity peak suggests resuspension/clogging"
                if turbidity_jump
                else "Turbidity stable"
            ),
        )
    )

    # Industrial contamination signatures
    ph_anomaly = abs(r.ph - PH_MEAN) > 1.5 * PH_STD
    flags.append(
        EventSignal(
            name="pH anomaly shift",
            triggered=ph_anomaly,
            severity="medium" if ph_anomaly else "none",
            reason=(
                "pH deviated sharply from baseline; possible industrial discharge"
                if ph_anomaly
                else "pH within normal envelope"
            ),
        )
    )

    acid_spill = r.ph < PH_MEAN - 2 * PH_STD and r.turbidity > TURB_MEAN + TURB_STD
    flags.append(
        EventSignal(
            name="Industrial acid spill signature",
            triggered=acid_spill,
            severity="high" if acid_spill else "none",
            reason=(
                "Sharp pH drop with turbidity spike aligns with acid discharge"
                if acid_spill
                else "No acid spill signature"
            ),
        )
    )

    # Sensor drift / malfunction cross-check for drift rate
    if not malfunction and history:
        jump = r.turbidity - history[-1].turbidity
        if abs(jump) > 3 * TURB_STD:
            flags.append(
                EventSignal(
                    name="Sensor anomaly jump",
                    triggered=True,
                    severity="medium",
                    reason="Sudden multi-sigma jump beyond instrument noise",
                )
            )

    response_flags = [
        EventFlag(**signal.__dict__)
        for signal in flags
    ]
    summary = [f"{f.name}: {f.reason}" for f in response_flags if f.triggered]
    if not summary:
        summary.append("No acute events detected; continue routine monitoring.")

    return EventDetectionResponse(flags=response_flags, summary=summary)
