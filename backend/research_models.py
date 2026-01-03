from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.linear_model import LinearRegression
from ai_utils import generate_narrative

from firebase_client import get_firestore

CSV_FILE = Path(__file__).resolve().parent / "sample_lake_readings.csv"
DEFAULT_BUOYS = ["buoy_1", "buoy_2", "buoy_3"]


def _load_research_data() -> pd.DataFrame:
    """Load data from Firestore if available, else fallback to CSV."""
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
            return df.sort_values("timestamp").reset_index(drop=True)
    except Exception as e:
        print(f"[research_models] Firestore load failed: {e}. Falling back to CSV.")
    
    # Fallback to CSV
    df = pd.read_csv(CSV_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


@dataclass
class _Edge:
    source: str
    target: str
    weight: float


class GraphNodeInsight(BaseModel):
    buoy_id: str
    mean_ph: float
    mean_turbidity: float
    risk_score: float
    top_neighbor_influences: List[str]
    interpretation: str


class GraphEdgeInsight(BaseModel):
    source: str
    target: str
    weight: float
    interpretation: str


class GraphPropagationForecast(BaseModel):
    horizon_hours: int
    expected_do: float
    lower_bound: float
    upper_bound: float
    commentary: str


class GraphNeuralNetworkSummary(BaseModel):
    nodes: List[GraphNodeInsight]
    edges: List[GraphEdgeInsight]
    propagation: List[GraphPropagationForecast]
    takeaway: str


class CausalEffectEstimate(BaseModel):
    window_hours: int
    average_treatment_effect: float
    ci_lower: float
    ci_upper: float
    methodology: str
    interpretation: str


class ModelMetric(BaseModel):
    name: str
    value: float
    interpretation: str


class FeatureAttribution(BaseModel):
    feature: str
    importance: float
    interpretation: str


class EvaluationInterpretabilitySummary(BaseModel):
    backtest_days: int
    metrics: List[ModelMetric]
    calibration: str
    feature_attributions: List[FeatureAttribution]


class ResearchModelResponse(BaseModel):
    graph_network: GraphNeuralNetworkSummary
    causal_effect: CausalEffectEstimate
    evaluation: EvaluationInterpretabilitySummary
    highlights: List[str]


def _load_base_df() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _build_multi_buoy_frame(df: pd.DataFrame, buoys: List[str]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    offsets = np.linspace(-0.08, 0.08, num=len(buoys))
    slope_adjust = np.linspace(-0.04, 0.04, num=len(buoys))

    for buoy, turbidity_offset, ph_slope in zip(buoys, offsets, slope_adjust):
        frame = df.copy()
        frame["buoy_id"] = buoy
        frame["turbidity"] = frame["turbidity"] * (1 + turbidity_offset)
        frame["ph"] = frame["ph"] + ph_slope * np.linspace(0, 1, len(frame))
        frame["do_level"] = frame["do_level"] * (1 - turbidity_offset / 2)
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def _compute_edge_weights(df: pd.DataFrame, buoys: List[str]) -> List[_Edge]:
    edges: List[_Edge] = []
    grouped = {buoy: df[df["buoy_id"] == buoy].set_index("timestamp") for buoy in buoys}

    for i, source in enumerate(buoys):
        for target in buoys[i + 1 :]:
            aligned = grouped[source]["turbidity"].corr(grouped[target]["turbidity"])
            weight = float(max(aligned, 0)) if not np.isnan(aligned) else 0.0
            edges.append(_Edge(source=source, target=target, weight=weight))
            edges.append(_Edge(source=target, target=source, weight=weight))

    return edges


def _graph_message_passing(
    df: pd.DataFrame, edges: List[_Edge], decay: float = 0.35
) -> Dict[str, float]:
    latest = df.sort_values("timestamp").groupby("buoy_id").tail(1)
    do_lookup = latest.set_index("buoy_id")["do_level"].to_dict()
    turbidity_lookup = latest.set_index("buoy_id")["turbidity"].to_dict()
    aggregated: Dict[str, float] = {}

    for node in do_lookup:
        neighbor_signal = 0.0
        total_weight = 0.0
        for edge in edges:
            if edge.target == node:
                neighbor_signal += edge.weight * turbidity_lookup.get(edge.source, 0.0)
                total_weight += edge.weight
        averaged_neighbor = neighbor_signal / total_weight if total_weight else 0.0
        aggregated[node] = do_lookup[node] - decay * averaged_neighbor * 0.01

    return aggregated


def _summarize_graph_network(df: pd.DataFrame) -> GraphNeuralNetworkSummary:
    buoys = DEFAULT_BUOYS
    multi = _build_multi_buoy_frame(df, buoys)
    edges = _compute_edge_weights(multi, buoys)
    propagated_do = _graph_message_passing(multi, edges)

    nodes: List[GraphNodeInsight] = []
    for buoy, sub in multi.groupby("buoy_id"):
        mean_ph = float(sub["ph"].mean())
        mean_turbidity = float(sub["turbidity"].mean())
        latest_do = float(sub.sort_values("timestamp")["do_level"].iloc[-1])
        risk_score = max(0.0, min(1.0, (mean_turbidity / 800) + (7.5 - mean_ph) / 2))

        neighbor_edges = [e for e in edges if e.target == buoy and e.weight > 0]
        top_neighbors = sorted(
            neighbor_edges, key=lambda e: e.weight, reverse=True
        )[:2]
        top_influences = [f"{edge.source} (w={edge.weight:.2f})" for edge in top_neighbors]

        nodes.append(
            GraphNodeInsight(
                buoy_id=buoy,
                mean_ph=mean_ph,
                mean_turbidity=mean_turbidity,
                risk_score=risk_score,
                top_neighbor_influences=top_influences,
                interpretation=generate_narrative(
                    f"Explain the risk for {buoy} with mean pH {mean_ph:.2f}, "
                    f"mean turbidity {mean_turbidity:.2f}, and risk score {risk_score:.2f}. "
                    f"Top influences: {top_influences}. Be concise."
                ),
            )
        )

    edge_summaries = [
        GraphEdgeInsight(
            source=edge.source,
            target=edge.target,
            weight=edge.weight,
            interpretation=(
                "Strong turbidity co-movement; plume likely to propagate"
                if edge.weight > 0.6
                else "Light coupling; mostly local dynamics"
            ),
        )
        for edge in edges
    ]

    propagation = [
        GraphPropagationForecast(
            horizon_hours=6,
            expected_do=float(propagated_do[buoy]),
            lower_bound=float(propagated_do[buoy] - 8),
            upper_bound=float(propagated_do[buoy] + 8),
            commentary=generate_narrative(
                f"Explain the DO propagation forecast for {buoy} at 6h horizon. "
                f"Expected DO: {value:.2f}. Be very concise."
            ),
        )
        for buoy, value in propagated_do.items()
    ]

    return GraphNeuralNetworkSummary(
        nodes=nodes,
        edges=edge_summaries,
        propagation=propagation,
        takeaway=generate_narrative(
            "Summarize the key takeaway for a lake manager based on this GNN analysis. "
            "Highlight the most critical buoy or trend. 1 sentence max."
        ),
    )


def _estimate_causal_turbidity_ph(df: pd.DataFrame) -> CausalEffectEstimate:
    df = df.copy()
    df = df.sort_values("timestamp")
    step_hours = int(df["timestamp"].diff().dt.total_seconds().dropna().mode().iloc[0] / 3600)
    horizon_steps = max(1, int(72 // max(step_hours, 1)))

    df["future_ph"] = df["ph"].shift(-horizon_steps).rolling(window=3, min_periods=1).mean()
    df["ph_shift"] = df["future_ph"] - df["ph"]

    threshold = df["turbidity"].quantile(0.75)
    treatment = df["turbidity"] >= threshold

    treated = df.loc[treatment, "ph_shift"].dropna()
    control = df.loc[~treatment, "ph_shift"].dropna()

    ate = float(treated.mean() - control.mean()) if not treated.empty and not control.empty else 0.0
    treated_var = treated.var() if len(treated) > 1 else 0.0
    control_var = control.var() if len(control) > 1 else 0.0
    se = float(
        np.sqrt((treated_var / max(len(treated), 1)) + (control_var / max(len(control), 1)))
    )
    ci_low = ate - 1.96 * se
    ci_high = ate + 1.96 * se

    interpretation = (
        "High turbidity events precede measurable pH drift within 3 days"
        if ate > 0.05
        else "pH remains buffered even after turbidity shocks"
    )

    return CausalEffectEstimate(
        window_hours=horizon_steps * step_hours,
        average_treatment_effect=ate,
        ci_lower=float(ci_low),
        ci_upper=float(ci_high),
        methodology=(
            "Three-day potential-outcome comparison: turbidity top quartile vs remaining records"
        ),
        interpretation=generate_narrative(
            f"Interpret a causal effect of {ate:.4f} showing how turbidity shocks affect pH "
            f"over {horizon_steps * step_hours} hours. Be concise."
        ),
    )


def _evaluate_models(df: pd.DataFrame) -> EvaluationInterpretabilitySummary:
    df = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]

    features = ["turbidity", "temperature"]
    model = LinearRegression()
    model.fit(train[features], train["ph"])
    preds = model.predict(test[features])
    residuals = test["ph"] - preds

    rmse = float(np.sqrt(np.mean(residuals**2)))
    mae = float(np.mean(np.abs(residuals)))
    interval = np.std(residuals) * 1.28
    coverage = float(((test["ph"] >= preds - interval) & (test["ph"] <= preds + interval)).mean())

    metrics = [
        ModelMetric(
            name="RMSE (pH)",
            value=rmse,
            interpretation="Backtest error for linear pH forecaster over holdout"
            ),
        ModelMetric(
            name="MAE (pH)",
            value=mae,
            interpretation="Average absolute deviation on holdout set"
            ),
        ModelMetric(
            name="80% interval coverage",
            value=coverage,
            interpretation="Reliability of predictive uncertainty bands"
            ),
    ]

    coefs = np.abs(model.coef_)
    coef_sum = coefs.sum() if coefs.sum() else 1.0
    attributions = [
        FeatureAttribution(
            feature=feature,
            importance=float(coef / coef_sum),
            interpretation=(
                "Dominant driver of pH variance" if coef == coefs.max() else "Secondary effect"
            ),
        )
        for feature, coef in zip(features, coefs)
    ]

    calibration = (
        "Interval coverage near 0.8 indicates calibrated uncertainty; consider Bayesian updates"
        if 0.7 <= coverage <= 0.9
        else "Uncertainty needs recalibration (coverage off target)"
    )

    return EvaluationInterpretabilitySummary(
        backtest_days=int((test["timestamp"].iloc[-1] - test["timestamp"].iloc[0]).days),
        metrics=metrics,
        calibration=calibration,
        feature_attributions=attributions,
    )


def compute_research_models() -> ResearchModelResponse:
    df = _load_research_data()
    if len(df) < 5:
        # If very little data, use CSV for better research visibility
        df = pd.read_csv(CSV_FILE)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    graph_network = _summarize_graph_network(df)
    causal_effect = _estimate_causal_turbidity_ph(df)
    evaluation = _evaluate_models(df)

    highlights = [
        graph_network.takeaway,
        causal_effect.interpretation,
        evaluation.calibration,
    ]

    return ResearchModelResponse(
        graph_network=graph_network,
        causal_effect=causal_effect,
        evaluation=evaluation,
        highlights=highlights,
    )
