from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze rollout label quality or emit a graceful template when labels are not ready.")
    parser.add_argument("--input", default="experiments/nn_ranker_v1/phase5_ntu_rollout/labeled_candidates_rollout.parquet")
    parser.add_argument("--output", default="experiments/nn_ranker_v1/phase5_sidecar/rollout_label_quality_template.md")
    args = parser.parse_args()

    input_path = REPO_ROOT / args.input
    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase 5 Sidecar Rollout Label Quality Template",
        "",
        f"- expected_input: `{args.input}`",
    ]
    if not input_path.exists():
        lines.extend(
            [
                "- status: `waiting_for_phase5_rollout_aggregate`",
                "- warning: Phase 5 NTU rollout aggregate file does not exist yet, so this dashboard remains a template.",
                "",
                "## Planned Checks",
                "",
                "- row count",
                "- states count",
                "- mission distribution",
                "- 2p/4p balance",
                "- phase balance",
                "- delta_score_80 distribution",
                "- proxy_value vs delta_score_80 correlation",
                "- mission-wise rollout value",
                "- hold anchor comparison",
                "- noise/outlier rows",
                "- training recommendation",
            ]
        )
    else:
        lines.extend(
            [
                "- status: `input_present_but_sidecar_template_mode`",
                "- note: extend this tool to parse parquet in a fully offline-safe environment when the aggregated Phase 5 label file is ready.",
            ]
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "input_exists": input_path.exists()}, sort_keys=True))


if __name__ == "__main__":
    main()
