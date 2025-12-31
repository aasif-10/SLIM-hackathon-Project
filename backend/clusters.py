from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA


class KMeansClusterInfo(BaseModel):
    cluster: int
    label: str
    count: int


class DBSCANPatterns(BaseModel):
    core_points: int
    noise_points: int
    clusters_found: int


class PCAProjectionPoint(BaseModel):
    timestamp: str
    pc1: float
    pc2: float


class SeasonalSummary(BaseModel):
    summer: int
    monsoon: int
    winter: int


class ClusterPatternsResponse(BaseModel):
    kmeans_clusters: List[KMeansClusterInfo]
    dbscan_patterns: DBSCANPatterns
    pca_projection: List[PCAProjectionPoint]
    seasonal_clusters: SeasonalSummary


CSV_FILE = Path(__file__).resolve().parent / "sample_lake_readings.csv"

df = pd.read_csv(CSV_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

cluster_df = df[["ph", "turbidity", "temperature"]].ffill()

kmeans = KMeans(n_clusters=3, random_state=42)
kmeans_labels = kmeans.fit_predict(cluster_df)

dbscan = DBSCAN(eps=0.5, min_samples=10)
dbscan_labels = dbscan.fit_predict(cluster_df)

pca = PCA(n_components=2)
pca_result = pca.fit_transform(cluster_df)
df["pc1"] = pca_result[:, 0]
df["pc2"] = pca_result[:, 1]


def _detect_season(month: int) -> str:
    if month in [3, 4, 5]:
        return "summer"
    if month in [6, 7, 8, 9]:
        return "monsoon"
    return "winter"


df["season"] = df["timestamp"].dt.month.apply(_detect_season)


def compute_cluster_patterns(
    supabase: Optional[object] = None,
) -> ClusterPatternsResponse:
    """Compute clustering and pattern summaries and optionally store them."""

    unique, counts = np.unique(kmeans_labels, return_counts=True)
    kmeans_summary: List[KMeansClusterInfo] = []

    for cluster, count in zip(unique, counts):
        label = f"Cluster {cluster}"
        if cluster == 0:
            label = "Clean water condition"
        elif cluster == 1:
            label = "Moderate pollution"
        elif cluster == 2:
            label = "High turbidity period"

        kmeans_summary.append(
            KMeansClusterInfo(
                cluster=int(cluster),
                label=label,
                count=int(count),
            )
        )

    dbscan_summary = DBSCANPatterns(
        core_points=int(np.sum(dbscan_labels != -1)),
        noise_points=int(np.sum(dbscan_labels == -1)),
        clusters_found=int(len(set(dbscan_labels)) - (1 if -1 in dbscan_labels else 0)),
    )

    pca_output: List[PCAProjectionPoint] = []
    limit = min(200, len(df))
    for i in range(limit):
        pca_output.append(
            PCAProjectionPoint(
                timestamp=str(df["timestamp"].iloc[i]),
                pc1=float(df["pc1"].iloc[i]),
                pc2=float(df["pc2"].iloc[i]),
            )
        )

    seasonal_summary = SeasonalSummary(
        summer=int((df["season"] == "summer").sum()),
        monsoon=int((df["season"] == "monsoon").sum()),
        winter=int((df["season"] == "winter").sum()),
    )

    result = ClusterPatternsResponse(
        kmeans_clusters=kmeans_summary,
        dbscan_patterns=dbscan_summary,
        pca_projection=pca_output,
        seasonal_clusters=seasonal_summary,
    )

    if supabase is not None:
        try:
            cluster_map = {k.cluster: k for k in kmeans_summary}
            supabase.table("cluster_patterns").insert(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "kmeans_cluster_0_count": cluster_map.get(
                        0, KMeansClusterInfo(cluster=0, label="", count=0)
                    ).count,
                    "kmeans_cluster_0_label": cluster_map.get(
                        0, KMeansClusterInfo(cluster=0, label="", count=0)
                    ).label,
                    "kmeans_cluster_1_count": cluster_map.get(
                        1, KMeansClusterInfo(cluster=1, label="", count=0)
                    ).count,
                    "kmeans_cluster_1_label": cluster_map.get(
                        1, KMeansClusterInfo(cluster=1, label="", count=0)
                    ).label,
                    "kmeans_cluster_2_count": cluster_map.get(
                        2, KMeansClusterInfo(cluster=2, label="", count=0)
                    ).count,
                    "kmeans_cluster_2_label": cluster_map.get(
                        2, KMeansClusterInfo(cluster=2, label="", count=0)
                    ).label,
                    "dbscan_core_points": dbscan_summary.core_points,
                    "dbscan_noise_points": dbscan_summary.noise_points,
                    "dbscan_clusters_found": dbscan_summary.clusters_found,
                    "summer_count": seasonal_summary.summer,
                    "monsoon_count": seasonal_summary.monsoon,
                    "winter_count": seasonal_summary.winter,
                    "total_data_points": len(df),
                }
            ).execute()
        except Exception as exc:
            # non-fatal; just log to console
            print(f"[cluster_patterns] Error storing to Supabase: {exc}")

    return result
