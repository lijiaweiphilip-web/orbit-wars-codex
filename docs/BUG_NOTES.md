# Bug Notes

- `x/y` currently matches the local environment docs and action angle convention.
- Comets are removed before fleet launch; the agent should avoid relying on expiring comets.
- Multi-attacker combat resolves largest-vs-second-largest first, so third-party fights are noisy.
- Endgame long-range launches are filtered in the heuristic to avoid dead travel.
