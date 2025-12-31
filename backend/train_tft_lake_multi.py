import warnings

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="X does not have valid feature names, but StandardScaler was fitted with feature names",
)

import os
import shutil
from pathlib import Path

import torch
import pandas as pd

from lightning.pytorch import Trainer, seed_everything
from lightning.pytorch.loggers import CSVLogger
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint

from pytorch_forecasting.data import TimeSeriesDataSet, GroupNormalizer
from pytorch_forecasting.models import TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss


ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True, parents=True)

TARGETS = ["ph", "turbidity", "temperature", "do_level"]


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv("sample_lake_readings.csv")

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df = df.sort_values("timestamp").reset_index(drop=True)

    df["series_id"] = "buoy_1"

    df["time_idx"] = (
        (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() // 3600
    ).astype(int)

    for col in ["ph", "turbidity", "temperature", "do_level"]:
        if col in df.columns:
            df[col] = df[col].interpolate().bfill().ffill()
        else:
            raise ValueError(f"Column '{col}' not found in CSV")

    return df


def build_datasets(df: pd.DataFrame, target: str):
    group_lengths = df.groupby("series_id")["time_idx"].nunique()
    min_length = int(group_lengths.min())

    if min_length < 10:
        raise ValueError(
            f"Time series too short (min length = {min_length}). "
            f"Need at least ~10 timesteps to train."
        )

    max_prediction_length = min(24, max(1, min_length // 10))
    max_encoder_length = min(72, max(4, min_length - max_prediction_length))

    min_encoder_length = 1
    min_prediction_length = 1

    print(
        f"[{target}] window config -> "
        f"min_series_length={min_length}, "
        f"max_encoder_length={max_encoder_length}, "
        f"max_prediction_length={max_prediction_length}, "
        f"min_encoder_length={min_encoder_length}, "
        f"min_prediction_length={min_prediction_length}"
    )

    training = TimeSeriesDataSet(
        df,
        time_idx="time_idx",
        target=target,
        group_ids=["series_id"],
        max_encoder_length=max_encoder_length,
        max_prediction_length=max_prediction_length,
        min_encoder_length=min_encoder_length,
        min_prediction_length=min_prediction_length,
        time_varying_unknown_reals=["ph", "turbidity", "temperature", "do_level"],
        time_varying_known_reals=["time_idx"],
        static_categoricals=["series_id"],
        target_normalizer=GroupNormalizer(groups=["series_id"]),
        allow_missing_timesteps=True,
    )

    train_dl = training.to_dataloader(
        train=True,
        batch_size=64,
        num_workers=0,  # 0 on Windows
        shuffle=True,
    )

    return training, train_dl


def build_model(training: TimeSeriesDataSet) -> TemporalFusionTransformer:
    model = TemporalFusionTransformer.from_dataset(
        training,
        hidden_size=32,
        attention_head_size=4,
        dropout=0.1,
        hidden_continuous_size=16,
        loss=QuantileLoss(),
        output_size=7,  # default TFT quantiles
        learning_rate=1e-3,
    )

    print(f"Model size: {model.size()/1e3:.1f}k parameters")
    return model


def build_trainer(target: str):
    early_stop = EarlyStopping(
        monitor="train_loss",
        patience=5,
        mode="min",
    )

    checkpoint_cb = ModelCheckpoint(
        dirpath=f"checkpoints/{target}",
        filename=f"tft-{target}" + "-{epoch:02d}-{train_loss:.4f}",
        monitor="train_loss",
        mode="min",
        save_top_k=1,
    )

    logger = CSVLogger("logs", name=f"tft_{target}")

    torch.set_float32_matmul_precision("medium")

    trainer = Trainer(
        accelerator="auto",
        devices=1,
        max_epochs=40,
        logger=logger,
        callbacks=[early_stop, checkpoint_cb],
    )

    return trainer, checkpoint_cb


def main():
    seed_everything(42)
    print("Seed set to 42")

    print("Loading dataset...")
    df = load_dataset()

    for target in TARGETS:
        print("\n" + "=" * 60)
        print(f"Training TFT model for target: {target}")
        print("=" * 60)

        training, train_dl = build_datasets(df, target)
        model = build_model(training)
        trainer, ckpt_cb = build_trainer(target)

        print(f"[{target}] Training started...")
        trainer.fit(model, train_dataloaders=train_dl)
        print(f"[{target}] Training completed!")

        # save best checkpoint + dataset definition into artifacts/
        best_ckpt = ckpt_cb.best_model_path
        if best_ckpt and os.path.exists(best_ckpt):
            dst_ckpt = ARTIFACT_DIR / f"tft_{target}_best.ckpt"
            shutil.copy(best_ckpt, dst_ckpt)
            print(f"[{target}] Saved best checkpoint → {dst_ckpt}")

        ds_path = ARTIFACT_DIR / f"tft_{target}_dataset.pkl"
        training.save(str(ds_path))
        print(f"[{target}] Saved dataset definition → {ds_path}")


if __name__ == "__main__":
    main()
