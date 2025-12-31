from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.feature_selection import mutual_info_regression

CSV_FILE = Path(__file__).resolve().parent / "sample_lake_readings.csv"


def _detect_season(month: int) -> str:
    if month in [3, 4, 5]:
        return "summer"
    if month in [6, 7, 8, 9]:
        return "monsoon"
    return "winter"


@dataclass
class _LagResult:
    lag_steps: int
    correlation: float


class CorrelationSummary(BaseModel):
    feature_x: str
    feature_y: str
    pearson: float
    interpretation: str


class LagCorrelationSummary(BaseModel):
    feature_x: str
    feature_y: str
    lag_hours: int
    correlation: float
    interpretation: str


class MutualInformationSummary(BaseModel):
    target: str
    feature: str
    score: float
    interpretation: str


class SeasonalPHSummary(BaseModel):
    season: str
    mean_ph: float
    std_ph: float
    interpretation: str


class MixingCycleSignal(BaseModel):
    cycles_detected: int
    avg_amplitude: float
    interpretation: str


class RelationshipAnalysisResponse(BaseModel):
    quick_facts: List[str]
    correlations: List[CorrelationSummary]
    lag_correlations: List[LagCorrelationSummary]
    mutual_information: List[MutualInformationSummary]
    seasonal_ph: List[SeasonalPHSummary]
    mixing_cycles: MixingCycleSignal


df = pd.read_csv(CSV_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)


def _pearson(x: str, y: str) -> float:
    return float(df[[x, y]].corr().iloc[0, 1])


def _correlation_label(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 0.75:
        strength = "very strong"
    elif magnitude >= 0.5:
        strength = "strong"
    elif magnitude >= 0.3:
        strength = "moderate"
    else:
        strength = "weak"
    direction = "positive" if value >= 0 else "negative"
    return f"{strength} {direction} correlation"


def _best_lagged_corr(
    feature_x: str, feature_y: str, max_lag_steps: int = 8
) -> _LagResult:
    base_step_hours = (
        df["timestamp"].diff().dt.total_seconds().dropna().mode().iloc[0] / 3600
    )
    best = _LagResult(lag_steps=0, correlation=0.0)
    for lag in range(-max_lag_steps, max_lag_steps + 1):
        if lag == 0:
            continue
        shifted = df[feature_y].shift(lag)
        aligned = df[[feature_x]].copy()
        aligned[feature_y] = shifted
        aligned = aligned.dropna()
        if aligned.empty:
            continue
        corr = aligned.corr().iloc[0, 1]
        if np.isnan(corr):
            continue
        if abs(corr) > abs(best.correlation):
            best = _LagResult(lag_steps=lag, correlation=float(corr))
    return _LagResult(lag_steps=int(best.lag_steps * base_step_hours), correlation=best.correlation)


def _mutual_information(target: str, features: List[str]) -> List[MutualInformationSummary]:
    X = df[features]
    y = df[target]
    scores = mutual_info_regression(X, y, random_state=42)
    results: List[MutualInformationSummary] = []
    for feature, score in sorted(zip(features, scores), key=lambda x: x[1], reverse=True):
        interpretation = (
            "Strong information for predicting dissolved oxygen" if score > 0.3 else "Some signal but less dominant"
        )
        results.append(
            MutualInformationSummary(
                target=target,
                feature=feature,
                score=float(score),
                interpretation=interpretation,
            )
        )
    return results


def _seasonal_ph_flattening() -> List[SeasonalPHSummary]:
    seasonal_df = df.copy()
    seasonal_df["season"] = seasonal_df["timestamp"].dt.month.apply(_detect_season)
    summaries: List[SeasonalPHSummary] = []
    grouped = seasonal_df.groupby("season")["ph"]
    overall_std = seasonal_df["ph"].std()
    for season, values in grouped:
        std_val = float(values.std())
        interpretation = (
            "Flatter pH profile; likely buffered" if std_val < overall_std else "More variable pH pattern"
        )
        summaries.append(
            SeasonalPHSummary(
                season=season,
                mean_ph=float(values.mean()),
                std_ph=std_val,
                interpretation=interpretation,
            )
        )
    return sorted(summaries, key=lambda s: s.season)


def _mixing_cycle_signal() -> MixingCycleSignal:
    temp_diff = df["temperature"].diff().dropna()
    threshold = temp_diff.std()
    significant = temp_diff[abs(temp_diff) > threshold]
    sign_change = (significant.shift().fillna(0) * significant) < 0
    cycles = int(sign_change.sum())
    avg_amp = float(significant.abs().mean()) if not significant.empty else 0.0
    interpretation = (
        "Pronounced temperature swings hint at recent mixing" if cycles > 0 else "Stable column; limited mixing cues"
    )
    return MixingCycleSignal(
        cycles_detected=cycles,
        avg_amplitude=avg_amp,
        interpretation=interpretation,
    )


def compute_relationship_insights() -> RelationshipAnalysisResponse:
    correlations = [
        CorrelationSummary(
            feature_x="temperature",
            feature_y="do_level",
            pearson=_pearson("temperature", "do_level"),
            interpretation="Higher temps reduce dissolved oxygen carrying capacity",
        ),
        CorrelationSummary(
            feature_x="turbidity",
            feature_y="ph",
            pearson=_pearson("turbidity", "ph"),
            interpretation="Particles and algal blooms can shift pH balance",
        ),
        CorrelationSummary(
            feature_x="turbidity",
            feature_y="temperature",
            pearson=_pearson("turbidity", "temperature"),
            interpretation="Suspended solids may track inflow and mixing events",
        ),
    ]

    temp_do_lag = _best_lagged_corr("temperature", "do_level")
    turbidity_ph_lag = _best_lagged_corr("turbidity", "ph")

    lag_relationships = [
        LagCorrelationSummary(
            feature_x="temperature",
            feature_y="do_level",
            lag_hours=temp_do_lag.lag_steps,
            correlation=temp_do_lag.correlation,
            interpretation=(
                "Delayed oxygen drop after warming could signal fish-kill risk"
            ),
        ),
        LagCorrelationSummary(
            feature_x="turbidity",
            feature_y="ph",
            lag_hours=turbidity_ph_lag.lag_steps,
            correlation=turbidity_ph_lag.correlation,
            interpretation="pH drift following turbidity spikes suggests biogeochemical response",
        ),
    ]

    mi_scores = _mutual_information("do_level", ["temperature", "ph", "turbidity"])
    seasonal_ph = _seasonal_ph_flattening()
    mixing_signal = _mixing_cycle_signal()

    quick_facts = [
        f"Temperature vs DO: {_correlation_label(correlations[0].pearson)}",
        f"Turbidity vs pH: {_correlation_label(correlations[1].pearson)}",
        f"Best temperature→DO lag: {lag_relationships[0].lag_hours}h ({_correlation_label(lag_relationships[0].correlation)})",
        f"Top DO driver by mutual information: {mi_scores[0].feature}",
    ]

    return RelationshipAnalysisResponse(
        quick_facts=quick_facts,
        correlations=[
            CorrelationSummary(
                **c.model_dump(),
                interpretation=f"{_correlation_label(c.pearson)}; {c.interpretation}",
            )
            for c in correlations
        ],
        lag_correlations=[
            LagCorrelationSummary(
                **l.model_dump(),
                interpretation=f"{_correlation_label(l.correlation)}; {l.interpretation}",
            )
            for l in lag_relationships
        ],
        mutual_information=mi_scores,
        seasonal_ph=seasonal_ph,
        mixing_cycles=mixing_signal,
    )
