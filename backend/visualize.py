from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

CSV_PATH = Path(__file__).parent / "sample_lake_readings.csv"
SENSOR_COLUMNS = ["ph", "turbidity", "temperature", "do_level"]


def load_data():
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    for col in SENSOR_COLUMNS:
        df[f"{col}_smooth"] = df[col].rolling(window=8, min_periods=3).mean()

    df["month"] = df["timestamp"].dt.month_name()
    return df


def plot_timeseries(df):
    fig, axes = plt.subplots(len(SENSOR_COLUMNS), 1, sharex=True, figsize=(10, 8))
    fig.suptitle("Lake Sensor Time Series", fontsize=14)

    for ax, col in zip(axes, SENSOR_COLUMNS):
        ax.plot(df["timestamp"], df[col], label=f"{col} (raw)", alpha=0.4)
        ax.plot(
            df["timestamp"],
            df[f"{col}_smooth"],
            label=f"{col} (smooth)",
            linewidth=1.5,
        )
        ax.set_ylabel(col)
        ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Time")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])


def plot_monthly_boxplots(df):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    fig.suptitle("Monthly Distributions", fontsize=14)

    axes = axes.ravel()
    months_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    df["month"] = pd.Categorical(df["month"], categories=months_order, ordered=True)

    for ax, col in zip(axes, SENSOR_COLUMNS):
        df.boxplot(column=col, by="month", ax=ax, grid=False)
        ax.set_title(col)
        ax.set_xlabel("Month")
        ax.tick_params(axis="x", rotation=45)

    plt.suptitle("")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])


def plot_correlation(df):
    corr = df[SENSOR_COLUMNS].corr()

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")

    ax.set_xticks(range(len(SENSOR_COLUMNS)))
    ax.set_yticks(range(len(SENSOR_COLUMNS)))
    ax.set_xticklabels(SENSOR_COLUMNS, rotation=45, ha="right")
    ax.set_yticklabels(SENSOR_COLUMNS)

    for i in range(len(SENSOR_COLUMNS)):
        for j in range(len(SENSOR_COLUMNS)):
            ax.text(
                j,
                i,
                f"{corr.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="black",
                fontsize=8,
            )

    fig.colorbar(im, ax=ax, label="Correlation")
    ax.set_title("Sensor Correlation Matrix")
    fig.tight_layout()


def main():
    df = load_data()
    print(f"Loaded {len(df)} readings from {CSV_PATH.name}")

    plot_timeseries(df)
    plot_monthly_boxplots(df)
    plot_correlation(df)

    plt.show()


if __name__ == "__main__":
    main()

#hi