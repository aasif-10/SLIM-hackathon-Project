from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest
from ai_utils import generate_narrative


class LakeInput(BaseModel):
    ph: float
    turbidity: float
    temperature: float
    do_level: float


class AnomalyResult(BaseModel):
    is_anomaly: bool
    severity: str
    reason: str


class FullAnomalyResponse(BaseModel):
    ph_anomaly: AnomalyResult
    turbidity_anomaly: AnomalyResult
    temperature_anomaly: AnomalyResult
    do_anomaly: AnomalyResult
    pattern_anomaly: AnomalyResult


CSV_FILE = Path(__file__).resolve().parent / "sample_lake_readings.csv"

from functools import lru_cache

@lru_cache(maxsize=1)
def _get_anomaly_model_and_data():
    """Lazy load data and model for anomaly detection."""
    from firebase_client import get_firestore
    try:
        db = get_firestore()
        docs = db.collection("lake_readings").order_by("timestamp", direction="DESCENDING").limit(200).stream()
        data = [doc.to_dict() for doc in docs]
        if len(data) > 20:
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
        else:
            df = pd.read_csv(CSV_FILE)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
    except Exception:
        df = pd.read_csv(CSV_FILE)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    ph_stats = (df["ph"].mean(), df["ph"].std())
    turb_stats = (df["turbidity"].mean(), df["turbidity"].std())
    temp_stats = (df["temperature"].mean(), df["temperature"].std())

    if "do_level" in df.columns:
        do_stats = (df["do_level"].mean(), df["do_level"].std())
    else:
        do_stats = (None, None)

    train_df = df[["ph", "turbidity", "temperature"]].ffill()

    ml_model = IsolationForest(
        n_estimators=200,
        contamination=0.03,
        random_state=42,
    )
    ml_model.fit(train_df)
    
    return ml_model, ph_stats, turb_stats, temp_stats, do_stats


def _rule_check(
    value: float, mean: Optional[float], std: Optional[float], name: str
) -> AnomalyResult:
    if mean is None or std is None:
        return AnomalyResult(
            is_anomaly=False,
            severity="none",
            reason="Not enough data",
        )

    z = abs((value - mean) / (std + 1e-6))

    if z > 3:
        return AnomalyResult(
            is_anomaly=True,
            severity="high",
            reason=f"{name} extreme deviation",
        )
    if z > 2:
        return AnomalyResult(
            is_anomaly=True,
            severity="medium",
            reason=f"{name} moderate deviation",
        )
    if z > 1.5:
        return AnomalyResult(
            is_anomaly=True,
            severity="low",
            reason=f"{name} slight deviation",
        )

    return AnomalyResult(
        is_anomaly=False,
        severity="none",
        reason="Normal range",
    )


def _ml_check(ml_model, ph: float, turb: float, temp: float) -> bool:
    point = np.array([[ph, turb, temp]])
    return bool(ml_model.predict(point)[0] == -1)


def analyze_lake_reading(reading: LakeInput) -> FullAnomalyResponse:
    """Run rule-based + ML-based anomaly checks for one reading."""
    ml_model, ph_stats, turb_stats, temp_stats, do_stats = _get_anomaly_model_and_data()

    ph_res = _rule_check(reading.ph, ph_stats[0], ph_stats[1], "ph")
    turb_res = _rule_check(reading.turbidity, turb_stats[0], turb_stats[1], "turbidity")
    temp_res = _rule_check(reading.temperature, temp_stats[0], temp_stats[1], "temperature")

    if do_stats[0] is not None and do_stats[1] is not None:
        do_res = _rule_check(reading.do_level, do_stats[0], do_stats[1], "do_level")
    else:
        do_res = AnomalyResult(
            is_anomaly=False,
            severity="none",
            reason="DO not measured; baseline risk only",
        )

    ml_res = _ml_check(ml_model, reading.ph, reading.turbidity, reading.temperature)

    if any([ph_res.is_anomaly, turb_res.is_anomaly, temp_res.is_anomaly, do_res.is_anomaly, ml_res]):
        # Add AI detail if something is wrong
        ai_reason = generate_narrative(
            f"Given a lake reading with pH {reading.ph}, turbidity {reading.turbidity}, "
            f"temperature {reading.temperature}, and DO {reading.do_level}, "
            f"explain the primary concern if ph_anomaly={ph_res.is_anomaly}, "
            f"turb_anomaly={turb_res.is_anomaly}, ml_anomaly={ml_res}. 1 sentence."
        )
        if ml_res:
            pattern_reason = ai_reason
        else:
            pattern_reason = "Normal pattern"
    else:
        pattern_reason = "Normal pattern"

    pattern_anom = AnomalyResult(
        is_anomaly=ml_res,
        severity="high" if ml_res else "none",
        reason=pattern_reason,
    )

    return FullAnomalyResponse(
        ph_anomaly=ph_res,
        turbidity_anomaly=turb_res,
        temperature_anomaly=temp_res,
        do_anomaly=do_res,
        pattern_anomaly=pattern_anom,
    )


def anomaly_to_row(reading: LakeInput, result: FullAnomalyResponse):
    """Convert anomaly results + raw reading into a DB row."""
    return {
        "ph": reading.ph,
        "turbidity": reading.turbidity,
        "temperature": reading.temperature,
        "do_level": reading.do_level,
        "ph_is_anomaly": result.ph_anomaly.is_anomaly,
        "ph_severity": result.ph_anomaly.severity,
        "ph_reason": result.ph_anomaly.reason,
        "turbidity_is_anomaly": result.turbidity_anomaly.is_anomaly,
        "turbidity_severity": result.turbidity_anomaly.severity,
        "turbidity_reason": result.turbidity_anomaly.reason,
        "temperature_is_anomaly": result.temperature_anomaly.is_anomaly,
        "temperature_severity": result.temperature_anomaly.severity,
        "temperature_reason": result.temperature_anomaly.reason,
        "do_is_anomaly": result.do_anomaly.is_anomaly,
        "do_severity": result.do_anomaly.severity,
        "do_reason": result.do_anomaly.reason,
        "pattern_is_anomaly": result.pattern_anomaly.is_anomaly,
        "pattern_severity": result.pattern_anomaly.severity,
        "pattern_reason": result.pattern_anomaly.reason,
    }
