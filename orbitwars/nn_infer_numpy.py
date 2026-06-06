from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable


def load_ranker_weights(path: str | Path) -> dict | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    required = {"feature_names", "mean", "std", "layers"}
    if not required.issubset(payload):
        return None
    return payload


def _linear(x: list[float], weight: list[list[float]], bias: list[float]) -> list[float]:
    out: list[float] = []
    for row, b in zip(weight, bias):
        total = float(b)
        for value, w in zip(x, row):
            total += value * float(w)
        out.append(total)
    return out


def _relu(values: Iterable[float]) -> list[float]:
    return [max(0.0, float(value)) for value in values]


def score_features(features: dict[str, float], weights: dict | None) -> float | None:
    if weights is None:
        return None
    names = weights["feature_names"]
    mean = weights["mean"]
    std = weights["std"]
    x = []
    for name in names:
        denom = float(std.get(name, 1.0)) or 1.0
        value = (float(features.get(name, 0.0)) - float(mean.get(name, 0.0))) / denom
        if not math.isfinite(value):
            value = 0.0
        x.append(value)
    layers = weights["layers"]
    x = _relu(_linear(x, layers[0]["weight"], layers[0]["bias"]))
    x = _relu(_linear(x, layers[1]["weight"], layers[1]["bias"]))
    out = _linear(x, layers[2]["weight"], layers[2]["bias"])
    return float(out[0])
