from pathlib import Path
import shutil
from pytorch_forecasting import TimeSeriesDataSet

ARTIFACT_DIR = Path("artifacts")
CHECKPOINT_SRC = Path("checkpoints")
DATASET_SRC = Path("tft_dataset.pkl")

ARTIFACT_DIR.mkdir(exist_ok=True)

ckpt_files = list(CHECKPOINT_SRC.glob("*.ckpt"))
if not ckpt_files:
    raise RuntimeError("No .ckpt found in ./checkpoints/")

ckpt_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
best_ckpt = ckpt_files[0]

target_ckpt = ARTIFACT_DIR / "tft_do_best.ckpt"
shutil.copy(best_ckpt, target_ckpt)
print(f"Copied checkpoint → {target_ckpt}")

if DATASET_SRC.exists():
    shutil.copy(DATASET_SRC, ARTIFACT_DIR / "tft_do_dataset.pkl")
    print("Copied dataset definition → artifacts/tft_do_dataset.pkl")
else:
    print(
        "WARNING: Dataset file tft_dataset.pkl not found. "
        "Retrain once with dataset.save(...) enabled."
    )
