"""Lightweight digital twin utilities for the lake using the 1-year CSV archive."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from ai_utils import generate_narrative

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
    temperature_rise_c: float = Field(1.5)
    pollution_event_strength: float = Field(0.35, ge=0.0, le=1.0)
    rainfall_mm: float = Field(20.0)

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
        if below.empty: continue
        end_ts = below.iloc[0]["timestamp"]
        hours = (end_ts - start_ts).total_seconds() / 3600
        if hours > 0: durations.append(hours)
    if not durations: return TurbidityRecovery(typical_hours=24.0, reference_spikes=0)
    return TurbidityRecovery(typical_hours=float(np.median(durations)), reference_spikes=len(durations))

def _format_confidence(count: int) -> str:
    if count >= 10: return "High (multiple historical matches)"
    if count >= 5: return "Medium (a few precedents)"
    if count >= 1: return "Directional (limited examples)"
    return "Heuristic only"

RECOVERY_BENCHMARK = _estimate_turbidity_recovery()

def simulate_digital_twin(payload: DigitalTwinRequest) -> DigitalTwinResponse:
    # 1) DO drop
    raw_drop = TEMP_DO_SLOPE * payload.temperature_rise_c
    do_drop = abs(raw_drop)
    projected_do = DO_MEAN - do_drop
    do_description = generate_narrative(
        f"Explain how a {payload.temperature_rise_c:.1f}°C temperature rise causes a "
        f"{do_drop:.2f} mg/L DO decline (slope {TEMP_DO_SLOPE:.3f}). Be concise (1 sentence)."
    )
    do_impact = f"Projected DO ≈ {projected_do:.2f} mg/L vs baseline {DO_MEAN:.2f}."

    # 2) Pollution shock
    turb_spike = TURB_STD * (1 + 3 * payload.pollution_event_strength)
    ph_dip = PH_STD * payload.pollution_event_strength
    do_penalty = DO_STD * (0.5 + payload.pollution_event_strength)
    pollution_description = generate_narrative(
        f"Describe a pollution event with intensity {payload.pollution_event_strength} causing "
        f"a {turb_spike:.0f} NTU turbidity spike and {do_penalty:.2f} mg/L oxygen loss. Be concise."
    )
    pollution_impact = f"Turbidity +{turb_spike:.0f} NTU, pH -{ph_dip:.2f}, DO -{do_penalty:.2f} mg/L."

    # 3) Recovery
    recovery = RECOVERY_BENCHMARK.typical_hours
    rainfall_factor = max(0.6, min(1.8, payload.rainfall_mm / 25))
    adj_recovery = recovery * rainfall_factor
    recovery_desc = generate_narrative(
        f"Explain why turbidity takes ~{adj_recovery:.1f}h to recover after {payload.rainfall_mm:.0f}mm rain. Be concise."
    )
    recovery_impact = f"Expected clearing in ~{adj_recovery:.1f}h based on {RECOVERY_BENCHMARK.reference_spikes} historical events."

    # 4) Bloom
    heat_s = max(0.0, (payload.temperature_rise_c + TEMP_MEAN - 27) / 5)
    turb_s = max(0.0, (TURB_BASELINE + turb_spike - 400) / 400)
    bloom_score = np.tanh(heat_s + turb_s)
    bloom_desc = generate_narrative(
        f"Interpret an algae bloom risk score of {bloom_score:.2f} given warming and turbidity. Be concise."
    )
    bloom_impact = f"Score: {bloom_score:.2f}. Maintenance of aerators recommended if >0.5."

    # 5) Mortality
    low_do_m = (DO_MEAN - do_penalty - do_drop)
    mort_s = np.tanh(max(0.0, (5 - low_do_m) / 2))
    mort_desc = generate_narrative(
        f"Explain fish mortality risk {mort_s:.2f} when projected local DO hits {low_do_m:.2f} mg/L. Be concise."
    )
    mort_impact = f"Mortality risk {mort_s:.2f}. Targets inlets and downwind coves."

    return DigitalTwinResponse(
        do_drop_scenario=ScenarioEstimate(
            description=do_description, impact=do_impact, confidence=_format_confidence(len(df))
        ),
        pollution_response=ScenarioEstimate(
            description=pollution_description, impact=pollution_impact, confidence=_format_confidence(RECOVERY_BENCHMARK.reference_spikes)
        ),
        turbidity_recovery=ScenarioEstimate(
            description=recovery_desc, impact=recovery_impact, confidence=_format_confidence(RECOVERY_BENCHMARK.reference_spikes)
        ),
        algae_bloom=ScenarioEstimate(
            description=bloom_desc, impact=bloom_impact, confidence="High (Enveloped)"
        ),
        fish_mortality_risk=ScenarioEstimate(
            description=mort_desc, impact=mort_impact, confidence=_format_confidence(len(df))
        ),
    )
