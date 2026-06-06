from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .nn_features import FEATURE_NAMES


META_COLUMNS = {"game", "mode", "seed", "step", "phase", "mission_type", "heuristic_score", "state_id", "candidate_id"}


def load_candidate_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.read_pickle(path)


def split_by_game_seed(
    table: pd.DataFrame,
    *,
    train_frac: float = 0.8,
    seed: int = 20260605,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    keys = table[["game", "seed"]].drop_duplicates().to_numpy().copy()
    rng.shuffle(keys)
    n_train = max(1, int(len(keys) * train_frac))
    train_keys = {tuple(row) for row in keys[:n_train]}
    mask = table[["game", "seed"]].apply(lambda row: (row["game"], row["seed"]) in train_keys, axis=1)
    return table[mask].copy(), table[~mask].copy()


def standardize_features(
    train: pd.DataFrame,
    valid: pd.DataFrame | None = None,
    *,
    feature_names: Iterable[str] = FEATURE_NAMES,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None, dict[str, dict[str, float]]]:
    features = [name for name in feature_names if name in train.columns]
    means = train[features].mean().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    stds = train[features].std().replace([np.inf, -np.inf], 1.0).fillna(1.0)
    stds = stds.mask(stds < 1e-6, 1.0)
    stats = {
        "features": features,
        "mean": {name: float(means[name]) for name in features},
        "std": {name: float(stds[name]) for name in features},
    }

    def apply(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out[features] = (out[features] - means) / stds
        out[features] = out[features].replace([np.inf, -np.inf], 0.0).fillna(0.0)
        return out

    train_std = apply(train)
    valid_std = apply(valid) if valid is not None else None
    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    return train_std, valid_std, stats


def make_pairwise_dataset(
    table: pd.DataFrame,
    *,
    label_column: str = "proxy_value",
    max_pairs_per_state: int = 8,
    seed: int = 20260605,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, int | float | str]] = []
    for state_id, group in table.groupby("state_id", sort=False):
        if len(group) < 2:
            continue
        ordered = group.sort_values(label_column, ascending=False)
        top = ordered.head(min(3, len(ordered)))
        bottom = ordered.tail(min(3, len(ordered)))
        hold = group[group["mission_type"] == "hold"].head(1)
        pairs = []
        for _, a in top.iterrows():
            for _, b in bottom.iterrows():
                if a["candidate_id"] != b["candidate_id"]:
                    pairs.append((a, b))
        if not hold.empty:
            h = hold.iloc[0]
            for _, a in top.iterrows():
                if a["candidate_id"] != h["candidate_id"]:
                    pairs.append((a, h))
        if len(pairs) > max_pairs_per_state:
            picks = rng.choice(len(pairs), size=max_pairs_per_state, replace=False)
            pairs = [pairs[int(idx)] for idx in picks]
        for a, b in pairs:
            rows.append(
                {
                    "state_id": state_id,
                    "cand_a": int(a["candidate_id"]),
                    "cand_b": int(b["candidate_id"]),
                    "row_a": int(a.name),
                    "row_b": int(b.name),
                    "mission_a": str(a["mission_type"]),
                    "mission_b": str(b["mission_type"]),
                    "label_a_better": 1 if float(a[label_column]) >= float(b[label_column]) else 0,
                }
            )
    return pd.DataFrame(rows)


def make_mission_balanced_sampler(table: pd.DataFrame) -> np.ndarray:
    counts = table["mission_type"].value_counts().to_dict()
    weights = table["mission_type"].map(lambda mission: 1.0 / max(1, counts.get(mission, 1))).to_numpy(dtype=np.float32)
    weights /= max(float(weights.mean()), 1e-12)
    return weights
