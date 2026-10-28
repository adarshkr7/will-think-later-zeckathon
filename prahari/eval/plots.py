"""Headless benchmark figures built from persisted output tables."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from prahari.data.firewall import assert_real


def calibration_plot(table: pd.DataFrame, destination: Path) -> None:
    assert_real(table)
    visible = table.loc[table["count"].gt(0)]
    figure, axes = plt.subplots(figsize=(6, 5), layout="constrained")
    axes.plot([0, 1], [0, 1], linestyle="--", color="0.6", label="Perfect calibration")
    axes.plot(visible.mean_probability, visible.observed_rate, marker="o", label="Outer-fold predictions")
    axes.set(xlabel="Mean predicted probability", ylabel="Observed default rate",
             xlim=(0, 1), ylim=(0, 1), title="Benchmark development calibration")
    axes.legend()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=150)
    plt.close(figure)
