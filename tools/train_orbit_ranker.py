from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a small Orbit Wars action-value ranker.")
    parser.add_argument("--data", default="experiments/ranker_dataset/orbit_ranker_examples.npz")
    parser.add_argument("--output-dir", default="experiments/ranker_model")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    data = np.load(args.data, allow_pickle=True)
    x = data["x"].astype("float32")
    y = data["y"].astype("float32")
    feature_names = [str(name) for name in data["feature_names"]]
    rng = np.random.default_rng(20260605)
    order = rng.permutation(len(x))
    split = int(len(x) * 0.9)
    train_idx = order[:split]
    valid_idx = order[split:]
    mean = x[train_idx].mean(axis=0)
    std = x[train_idx].std(axis=0) + 1e-6
    y_mean = float(y[train_idx].mean())
    y_std = float(y[train_idx].std() + 1e-6)
    x_train = (x[train_idx] - mean) / std
    x_valid = (x[valid_idx] - mean) / std
    y_train = (y[train_idx] - y_mean) / y_std
    y_valid = (y[valid_idx] - y_mean) / y_std

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = nn.Sequential(
        nn.Linear(x.shape[1], args.hidden),
        nn.ReLU(),
        nn.Linear(args.hidden, args.hidden),
        nn.ReLU(),
        nn.Linear(args.hidden, 1),
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    loss_fn = nn.SmoothL1Loss()
    loader = DataLoader(
        TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train[:, None])),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=2,
        pin_memory=(device == "cuda"),
    )
    valid_x = torch.from_numpy(x_valid).to(device)
    valid_y = torch.from_numpy(y_valid[:, None]).to(device)
    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        seen = 0
        for xb, yb in loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            pred = model(xb)
            loss = loss_fn(pred, yb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total += float(loss.item()) * len(xb)
            seen += len(xb)
        model.eval()
        with torch.no_grad():
            valid_loss = float(loss_fn(model(valid_x), valid_y).item())
        row = {"epoch": epoch, "train_loss": total / max(1, seen), "valid_loss": valid_loss, "device": device}
        history.append(row)
        print(json.dumps(row))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_dir / "ranker.pt")
    np.savez(output_dir / "ranker_export.npz", mean=mean, std=std, y_mean=y_mean, y_std=y_std)
    (output_dir / "metadata.json").write_text(
        json.dumps({"feature_names": feature_names, "history": history, "device": device}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), "device": device, "valid_loss": history[-1]["valid_loss"]}))


if __name__ == "__main__":
    main()
