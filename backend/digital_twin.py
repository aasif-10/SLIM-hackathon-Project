"""Lightweight digital twin utilities for the lake using the 1-year CSV archive."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

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

TEMP_DO_SLOPE = float(np.polyfit(df["temperature"], df["do_level"], 1)[0])
TURB_BASELINE = float(df["turbidity"].median())
TURB_STD = float(df["turbidity"].std())
PH_MEAN = float(df["ph"].mean())
PH_STD = float(df["ph"].std())
DO_MEAN = float(df["do_level"].mean())
DO_STD = float(df["do_level"].std())
TEMP_MEAN = float(df["temperature"].mean())
TEMP_STD = float(df["temperature"].std())


@dataclass
class TurbidityRecovery:
    typical_hours: float
    reference_spikes: int


class DigitalTwinRequest(BaseModel):
    temperature_rise_c: float = Field(
        1.5,
        description="Projected surface temperature increase in Celsius",
    )
    pollution_event_strength: float = Field(
        0.35,
        ge=0.0,
        le=1.0,
        description="0-1 scaled shock magnitude for a pollution slug",
    )
    rainfall_mm: float = Field(
        20.0,
        description="Recent rainfall depth driving turbidity recovery time",
    )


class ScenarioEstimate(BaseModel):
    description: str
    impact: str
    confidence: str


class DigitalTwinResponse(BaseModel):
    do_drop_scenario: ScenarioEstimate
    pollution_response: ScenarioEstimate
    turbidity_recovery: ScenarioEstimate
    algae_bloom: ScenarioEstimate
    fish_mortality_risk: ScenarioEstimate


def _estimate_turbidity_recovery() -> TurbidityRecovery:
    threshold = TURB_BASELINE + TURB_STD
    durations: List[float] = []

    above = df[df["turbidity"] > threshold]
    for idx in above.index:
        start_ts = df.loc[idx, "timestamp"]
        below = df.loc[idx:][df["turbidity"] <= threshold]
        if below.empty:
            continue
        end_ts = below.iloc[0]["timestamp"]
        hours = (end_ts - start_ts).total_seconds() / 3600
        if hours > 0:
            durations.append(hours)

    if not durations:
        return TurbidityRecovery(typical_hours=24.0, reference_spikes=0)

    return TurbidityRecovery(
        typical_hours=float(np.median(durations)),
        reference_spikes=len(durations),
    )


def _format_confidence(count: int) -> str:
    if count >= 10:
        return "High (multiple historical matches)"
    if count >= 5:
        return "Medium (a few precedents)"
    if count >= 1:
        return "Directional (limited examples)"
    return "Heuristic only"


RECOVERY_BENCHMARK = _estimate_turbidity_recovery()


def _categorize_risk(score: float) -> str:
    if score >= 0.75:
        return "severe"
    if score >= 0.5:
        return "high"
    if score >= 0.35:
        return "elevated"
    return "mild"


def simulate_digital_twin(payload: DigitalTwinRequest) -> DigitalTwinResponse:
    # 1) DO drop from warming using learned slope
    raw_drop = TEMP_DO_SLOPE * payload.temperature_rise_c
    do_drop = abs(raw_drop)
    projected_do = DO_MEAN - do_drop
    do_description = (
        f"A {payload.temperature_rise_c:.1f}°C rise typically shaves {do_drop:.2f} mg/L of DO"
        f" (slope {TEMP_DO_SLOPE:.3f})."
    )
    do_impact = (
        f"Projected DO ≈ {projected_do:.2f} mg/L vs baseline {DO_MEAN:.2f}; monitor fish stress if <5 mg/L."
    )

    # 2) Pollution shock response
    turb_spike = TURB_STD * (1 + 3 * payload.pollution_event_strength)
    ph_dip = PH_STD * payload.pollution_event_strength
    do_penalty = DO_STD * (0.5 + payload.pollution_event_strength)
    pollution_description = (
        "Sudden inflow modeled as turbidity spike and acidity drift based on historical variance."
    )
    pollution_impact = (
        f"Turbidity could jump by ~{turb_spike:.0f} NTU, pH dip by {ph_dip:.2f}, "
        f"and DO loss of {do_penalty:.2f} mg/L; deploy booms/aeration within 2 hours."
    )

    # 3) Turbidity recovery time after rain
    recovery = RECOVERY_BENCHMARK.typical_hours
    rainfall_factor = max(0.6, min(1.8, payload.rainfall_mm / 25))
    adjusted_recovery = recovery * rainfall_factor
    recovery_description = (
        f"Historical spikes cleared in median {recovery:.1f}h across {RECOVERY_BENCHMARK.reference_spikes} events."
    )
    recovery_impact = (
        f"With {payload.rainfall_mm:.0f} mm rain, expect clarity normalization in ~{adjusted_recovery:.1f}h"
        " (assuming similar inflow)."
    )

    # 4) Algae bloom conditions
    heat_score = max(0.0, (payload.temperature_rise_c + TEMP_MEAN - 27) / 5)
    turbidity_score = max(0.0, (TURB_BASELINE + turb_spike - 400) / 400)
    ph_score = max(0.0, (PH_MEAN + 0.3 - 8) / 1.5)
    bloom_score = np.tanh(heat_score + turbidity_score + ph_score)
    bloom_description = (
        "Bloom risk blends warming, suspended solids, and alkaline shift (tanh-scaled)."
    )
    bloom_impact = (
        f"Composite bloom risk {bloom_score:.2f} ({_categorize_risk(bloom_score)});"
        " maintain DO sensors and consider algaecide standby."
    )

    # 5) Fish mortality risk zones
    low_do_margin = (DO_MEAN - do_penalty - do_drop)
    mortality_score = np.tanh(max(0.0, (5 - low_do_margin) / 2))
    mortality_description = (
        "Combines DO depletion from warming + pollutant oxygen demand to flag stress pockets."
    )
    mortality_impact = (
        f"Zones with DO <5 mg/L risk score {mortality_score:.2f} ({_categorize_risk(mortality_score)});"
        " target aerators near inlets and downwind coves."
    )

    return DigitalTwinResponse(
        do_drop_scenario=ScenarioEstimate(
            description=do_description,
            impact=do_impact,
            confidence=_format_confidence(len(df)),
        ),
        pollution_response=ScenarioEstimate(
            description=pollution_description,
            impact=pollution_impact,
            confidence=_format_confidence(int(RECOVERY_BENCHMARK.reference_spikes)),
        ),
        turbidity_recovery=ScenarioEstimate(
            description=recovery_description,
            impact=recovery_impact,
            confidence=_format_confidence(int(RECOVERY_BENCHMARK.reference_spikes)),
        ),
        algae_bloom=ScenarioEstimate(
            description=bloom_description,
            impact=bloom_impact,
            confidence="High (derived from full-year envelope)",
        ),
        fish_mortality_risk=ScenarioEstimate(
            description=mortality_description,
            impact=mortality_impact,
            confidence=_format_confidence(len(df)),
        ),
    )
