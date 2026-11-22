"""Measure the discrepancy for each paired reading and record the outputs."""

import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

import figrecipe as fr
import scitex_clew as clew
from scitex_stats import describe

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "inputs/observations.zip"
RESULTS = ROOT / "results"


def analyse():
    RESULTS.mkdir(exist_ok=True)
    with clew.project_root(ROOT), clew.session(script_path=str(Path(__file__))) as run:
        run.record_input(str(SOURCE))
        with ZipFile(SOURCE) as archive, archive.open("measurements.csv") as member:
            reader = csv.DictReader(io.TextIOWrapper(member, encoding="utf-8"))
            pairs = [(float(row["reference_mm"]), float(row["sensor_mm"])) for row in reader]

        errors = [reading - reference for reference, reading in pairs]
        values, names = describe([abs(error) for error in errors], funcs=["mean"])
        summary = {
            "count": len(pairs),
            "mean_absolute_error_mm": float(dict(zip(names, values, strict=True))["mean"]),
        }
        metrics = RESULTS / "metrics.json"
        metrics.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        run.record_output(str(metrics))

        figure, axes = fr.subplots()
        indexes = range(1, len(errors) + 1)
        axes.bar(list(indexes), errors, color="#305b83")
        axes.axhline(0, color="#333333", linewidth=0.8)
        axes.set(xlabel="Reading", ylabel="Sensor minus reference (mm)", xticks=list(indexes))
        output = RESULTS / "reading-errors.png"
        fr.save(figure, output, dpi=120, save_recipe=False, validate=False, verbose=False)
        run.record_output(str(output))


if __name__ == "__main__":
    analyse()
