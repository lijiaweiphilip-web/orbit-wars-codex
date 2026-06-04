# Final Report

- Date: 2026-06-02
- Status: local Orbit Wars workspace bootstrapped and submit path verified
- Best current submit path: `submission/agent.py`
- Current best params source: `experiments/best_params.json`

## Local Verification

- `python -m pytest -q`: 6 passed
- `python -m orbitwars.bug_checks --quick`: completed
- `python -m orbitwars.tournament --agents agents/heuristic_v0.py,random --mode 2p --games 6 --episode-steps 100`: win rate 0.3333, avg rank 1.6667
- `python -m orbitwars.tournament --agents agents/heuristic_v1.py,agents/heuristic_v0.py,random,random --mode 4p --games 4 --episode-steps 100`: win rate 0.25, avg rank 3.0 for agent 0
- `python -m orbitwars.tournament --agents submission/agent.py,random --mode 2p --games 4 --episode-steps 100`: win rate 0.25, avg rank 1.75
- `python -m orbitwars.sweeper --samples 3`: completed and refreshed `experiments/best_params.json`
- `submission.zip`: contains `agent.py` and `README_SUBMISSION.md`
- `python -m orbitwars.tournament --agents agents/heuristic_v1.py,random --mode 2p --games 6 --episode-steps 120 --tag opening_v1_2p_seq`: win rate 0.6667, avg rank 1.3333
- `python -m orbitwars.replay_tools --tag opening_v1_2p_seq`: step_50 planets 3.167, step_100 planets 4.333, home_alive 1.0
- `python -m orbitwars.tournament --agents agents/heuristic_v1.py,agents/heuristic_v0.py,random,random --mode 4p --games 6 --episode-steps 120 --tag opening_v1_4p_seq`: win rate 0.3333, avg rank 2.0
- `python -m orbitwars.replay_tools --tag opening_v1_4p_seq`: step_50 planets 2.5, step_100 planets 2.833, home_alive 1.0
- `python -m orbitwars.tournament --agents agents/heuristic_v1.py,agents/heuristic_v0.py,random,random --mode 4p --games 8 --episode-steps 120 --tag mid4p_regroup_v1`: win rate 0.375, avg rank 1.875
- `python -m orbitwars.replay_tools --tag mid4p_regroup_v1`: step_50 planets 3.0, step_100 planets 3.375, home_alive 1.0
- `python -m orbitwars.sparring --tag-prefix sparring_v1_mix`: completed reusable mixed-pool check across 2p and 4p
- `sparring_v1_mix` combined: 30 games, win rate 0.4667, avg rank 1.8667, step_50 planets 2.667, step_100 planets 3.4
- `sparring_v1_mix_2p_random`: win rate 0.6667, avg rank 1.3333
- `sparring_v1_mix_2p_v0`: win rate 0.8333, avg rank 1.1667
- `sparring_v1_mix_4p_mix_a`: avg rank 2.0
- `sparring_v1_mix_4p_mix_b`: avg rank 2.5
- `sparring_v1_mix_4p_mix_c`: avg rank 2.3333
- `docs/GITHUB_CLOUD_AGENT_PLAYBOOK.md`: added project-specific offload guidance for saving local memory
- `.github-cloud-agent/packets/`: added ready-to-paste GitHub cloud-agent issue packets for weak-table diagnostics and sparring-tooling work
- `python -m orbitwars.replay_tools --compare-tags sparring_v1_mix_4p_mix_a,sparring_v1_mix_4p_mix_b,sparring_v1_mix_4p_mix_c`: compares weak-table tags against a baseline in one command
- `python -m orbitwars.sparring --tag-prefix sparring_v2_recover`: latest mixed-pool run after 4p recovery expansion
- `sparring_v2_recover` combined: 30 games, win rate 0.6333, avg rank 1.7, avg score delta 59.6
- `sparring_v2_recover_4p_mix_a`: win rate 0.6667, avg rank 1.6667
- `sparring_v2_recover_4p_mix_b`: win rate 0.6667, avg rank 2.0
- `sparring_v2_recover_4p_mix_c`: win rate 0.3333, avg rank 2.3333
- `python -m orbitwars.replay_tools --compare-tags sparring_v1_mix_4p_mix_a,sparring_v2_recover_4p_mix_a`: avg rank delta -0.3333, step_100 planets +0.834
- `python -m orbitwars.replay_tools --compare-tags sparring_v1_mix_4p_mix_b,sparring_v2_recover_4p_mix_b`: avg rank delta -0.5, step_100 planets +0.5
- `python -m orbitwars.replay_tools --compare-tags sparring_v1_mix_4p_mix_c,sparring_v2_recover_4p_mix_c`: avg rank unchanged, but step_100 planets +0.666 and score delta improved by 122.17
- `python -m orbitwars.tournament --agents agents/heuristic_v1.py,random,random,agents/heuristic_v0.py --mode 4p --games 6 --episode-steps 120 --tag mixc_recovery3_v1`: avg rank still 2.3333
- `python -m orbitwars.replay_tools --tag mixc_recovery3_v1`: step_50 planets 3.333, step_100 ships 669.667, avg score delta improved to -112.83
- `python -m orbitwars.replay_tools --loss-report sparring_v2_recover_4p_mix_c`: lists loss seeds and checkpoint gaps vs the winner
- `python -m orbitwars.replay_tools --loss-report sparring_v2_recover_4p_mix_c`: pattern histogram shows `midgame_falloff: 3`, `early_deficit: 1`
- `.github/workflows/python-ci.yml`: remote `pytest` lane added for GitHub Actions
- `.github/workflows/lightweight-sparring.yml`: manual lightweight sparring lane added for GitHub Actions artifact runs
- `configs/sparring_pool.json`: added `github_light` pool for bounded remote smoke runs
- `scripts/prepare_github_cloud_agent_issue.py`: generates `issue.md`, `packet.json`, and `decision.md` for GitHub cloud-agent delegation
- `orbitwars/sparring.py --summary-path`: writes a JSON summary artifact for remote runs
- `scripts/render_sparring_summary.py`: turns remote sparring JSON into Markdown for GitHub Actions job summaries
- `docs/GITHUB_DAILY_CHECKLIST.md`: one-page routine for GitHub-first low-RAM usage
- `docs/GITHUB_SETUP.md`: first-time repo hookup guide for GitHub Actions and cloud-agent workflow
- `.github/ISSUE_TEMPLATE/cloud-agent-task.md`: ready-made issue template for cloud-agent delegation
- `.devcontainer/devcontainer.json`: Codespaces-ready low-RAM remote development setup
- `orbitwars/replay_tools.py --loss-report`: now includes winner histogram and `step_50 -> step_100` leader-transition diagnostics
- `orbitwars/replay_tools.py --loss-report`: now also includes `growth_step_50_to_100` for agent 0 and the eventual winner
- `mixc_leadguard_v1`: tested a narrow 4p lead-conversion guard, but it did not move rank or checkpoint summaries, so it was removed from the mainline
- `mixc_territory_v2`: tested a narrower 4p territory-conversion tweak that boosts cheap nearby expansion while capping over-send on midgame captures
- `python -m orbitwars.replay_tools --compare-tags sparring_v2_recover_4p_mix_c,mixc_territory_v2`: `mix_c` avg rank stayed flat at 2.3333, but score delta improved by 20.66, step_50 planets by 0.333, and step_100 planets by 0.167
- `python -m orbitwars.sparring --pool github_light --tag-prefix smoke_territory_v2`: no smoke regression on the light pool; combined win rate 0.8333 and avg rank 1.1667
- `mixc_frontier_v1`: tested a narrower "hold threatened frontier planets before attacking out" idea, but it produced the same `mix_c` rank and nearly identical loss shapes, so it was removed from the mainline
- `mixc_contested_v1`: tested a 4p contested-target tweak that penalizes high-pressure conversion targets and prefers safer nearby captures while leading
- `python -m orbitwars.replay_tools --compare-tags sparring_v2_recover_4p_mix_c,mixc_territory_v2,mixc_contested_v1`: `mixc_contested_v1` kept the same `mix_c` rank for now, but improved score delta to `-81.17`, step_100 planets to `3.667`, and step_100 ships to `684.333`
- `python -m orbitwars.sparring --pool github_light --tag-prefix smoke_contested_v1`: light-pool smoke stayed healthy at `win_rate 0.8333`, `avg_rank 1.1667`
- `mixc_proximity_v1`: refined the contested-target idea by adding a positional signal for whether we or an enemy planet is actually closer to the target
- `python -m orbitwars.replay_tools --compare-tags sparring_v2_recover_4p_mix_c,mixc_contested_v1,mixc_proximity_v1`: `mixc_proximity_v1` still holds rank at `2.3333`, but improves score delta further to `-73.17` and step_100 ships to `693.0`
- `python -m orbitwars.sparring --pool github_light --tag-prefix smoke_proximity_v1`: light-pool smoke still stayed healthy at `win_rate 0.8333`, `avg_rank 1.1667`
- `mixc_seataware_v1`: tested a strongest-rival seat-aware extension on top of `mixc_proximity_v1`, but it produced the same `mix_c` outcomes and was removed from the mainline

## Current Read

- Tooling is ready: environment import, observation parsing, 2p/4p local matches, sweep stub, and submission packaging all work.
- The main early-game failure mode was identified and improved: the old agent stayed on one planet through step 100, while the new opening heuristic now expands reliably in both 2p and 4p.
- 2p is now meaningfully stronger than the initial baseline and beats the random sparring bot in short runs.
- A reusable sparring pool now exists, so future heuristic changes can be checked against both `random` and `heuristic_v0` in one pass.
- 4p recovery expansion produced a real mixed-pool jump: `mix_a` and `mix_b` improved clearly, and `mix_c` now has better economy even though rank is still lagging.
- A wider 4p recovery window pushed `mix_c` economy a bit further, but still did not improve final rank, so the remaining bottleneck is now clearly post-expansion conversion rather than raw neutral growth.
- The new loss report points to a more specific failure mode: several `mix_c` losses are still competitive at `step_50`, then fall behind by `step_100`, especially in planet count and fleet mass versus the eventual winner.
- The loss classifier sharpens that read further: the dominant failure mode for `mix_c` is now clearly `midgame_falloff`, not broad opening weakness.
- The new leader-transition read sharpens it again: in most `mix_c` losses, agent 0 is still the `step_50` table leader, then a different opponent becomes the `step_100` leader, which points to weak lead-conversion rather than one fixed bad matchup slot.
- A narrow lead-conversion guard was tested directly against that hypothesis, but it produced no measurable improvement, so the remaining problem likely needs more specific sample-driven rules instead of another broad midgame switch.
- The new growth read narrows it further: in several `mix_c` losses, agent 0 still grows ships from `step_50` to `step_100`, but does not grow planets while the eventual winner grows both. That points more toward weak map-control conversion than simple underproduction.
- A narrower territory-conversion tweak does change behavior in the intended direction: `mix_c` now grows a bit more planets and ships by `step_50/100`, and the average score gap is smaller, but that extra economy still is not yet enough to flip final rank.
- A follow-up frontier-hold rule did not change the decisive loss patterns (`0->1`, `0->2`, `0->3` still remained), so the next useful change likely needs better seat-aware or target-order information rather than another generic "be more conservative" switch.
- A contested-target adjustment appears more promising than the frontier-hold idea: it still has not moved `mix_c` rank yet, but it improves both `step_100` economy and score gap more than the earlier territory-only tweak, which suggests target quality is a more fruitful direction than broad caution switches.
- Adding a direct proximity or positional contest signal pushes that same idea a bit further: the loss shapes are still the same, but the table-state quality by `step_100` continues improving, so target ordering remains the best current path even before rank flips.
- A strongest-rival seat-aware variant on top of the proximity signal turned out to be outcome-equivalent to `mixc_proximity_v1`, so it was removed instead of leaving no-op complexity in the mainline.
- GitHub cloud-agent handoff materials now exist in-repo, so script/tooling work can be offloaded without rebuilding the task scope each time.
- GitHub-side execution is now partly wired up, not just documented: `pytest` and bounded sparring can run on GitHub runners instead of the local 16 GB laptop.
- The remote path is safer now because GitHub Actions defaults to a dedicated small pool instead of the full mixed sparring suite.
- Remote sparring is easier to inspect now because GitHub can upload a compact JSON summary artifact alongside the raw CSV.
- Remote sparring is easier to scan directly in GitHub now because the workflow can publish a Markdown summary into the job page itself.
- The GitHub-first path is now easier to use day to day because the repo includes both a checklist and a dedicated cloud-agent issue template.
- First-time setup is now documented too, so the repo no longer depends on chat memory for the initial GitHub hookup steps.
- The repo is now Codespaces-ready, which is the cleanest way to move routine coding and light evaluation off a 16 GB laptop.
- Replay diagnostics now support multi-tag comparison, which makes weak-table triage much cheaper than running separate commands and manually diffing the output.
- Replay diagnostics now also surface which player takes over the table between checkpoints, which is more actionable for the remaining 4p problem than raw end-state rank alone.
- OpenSpiel emits unrelated warning noise during startup; it does not block Orbit Wars runs.

## Next 24h Plan

- Improve `mix_c` specifically: turn the new target-ordering gains into actual rank improvements.
- Focus on `midgame_falloff` seeds where we lead at `step_50` but still lose planets by `step_100`, especially seed patterns like `0->1`, `0->2`, and `0->3`.
- Keep pushing target-quality and positional ordering rather than broad global caution switches.
- Re-package submission from the new heuristic after the next validation round.
