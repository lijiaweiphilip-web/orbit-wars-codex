from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    notes = {
        "x_y_swap_needed": False,
        "comets_removed_before_launch": True,
        "combat_top_two_attackers_only": True,
        "final_step_long_range_attacks_are_risky": True,
        "source": "local orbit_wars README and environment schema inspection",
        "mode": "quick" if args.quick else "full",
    }
    Path("docs/BUG_NOTES.md").write_text(
        "# Bug Notes\n\n"
        "- `x/y` currently matches the local environment docs and action angle convention.\n"
        "- Comets are removed before fleet launch; the agent should avoid relying on expiring comets.\n"
        "- Multi-attacker combat resolves largest-vs-second-largest first, so third-party fights are noisy.\n"
        "- Endgame long-range launches are filtered in the heuristic to avoid dead travel.\n",
        encoding="utf-8",
    )
    print(json.dumps(notes, ensure_ascii=False))


if __name__ == "__main__":
    main()
