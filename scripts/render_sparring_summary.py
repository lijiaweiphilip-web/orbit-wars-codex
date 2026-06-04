from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_markdown(payload: dict[str, object]) -> str:
    combined = payload.get("combined", {})
    lines = [
        "# Lightweight Sparring Summary",
        "",
        f"- Pool: `{payload.get('pool', '')}`",
        f"- Tag prefix: `{payload.get('tag_prefix', '')}`",
        f"- Games: `{combined.get('games', 0)}`",
        f"- Win rate: `{combined.get('win_rate_agent0', 'n/a')}`",
        f"- Avg rank: `{combined.get('avg_rank_agent0', 'n/a')}`",
        f"- Avg score delta: `{combined.get('avg_score_delta_vs_best_other', 'n/a')}`",
        "",
        "## Matchups",
    ]
    for matchup in payload.get("matchups", []):
        lines.append(
            "- "
            + f"`{matchup.get('tag', '')}`"
            + f" | mode `{matchup.get('mode', '')}`"
            + f" | games `{matchup.get('games', 0)}`"
            + f" | win rate `{matchup.get('win_rate_agent0', 'n/a')}`"
            + f" | avg rank `{matchup.get('avg_rank_agent0', 'n/a')}`"
        )

    snapshot_summary = combined.get("snapshot_summary", {})
    if snapshot_summary:
        lines.extend(["", "## Snapshots"])
        for step_name, metrics in snapshot_summary.items():
            lines.append(
                "- "
                + f"`{step_name}`"
                + f" | planets `{metrics.get('planets', 'n/a')}`"
                + f" | ships `{metrics.get('ships', 'n/a')}`"
                + f" | home_alive `{metrics.get('home_alive', 'n/a')}`"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    payload = json.loads(Path(args.summary_json).read_text(encoding="utf-8"))
    markdown = render_markdown(payload)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
