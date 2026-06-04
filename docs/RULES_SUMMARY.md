# Rules Summary

- Environment name: `orbit_wars`
- Episode length: `500` turns by default
- Per-turn timeout: `1s`
- Action format: `[[from_planet_id, direction_angle, num_ships], ...]`
- Observation fields confirmed locally: `planets`, `fleets`, `player`, `step`, `angular_velocity`, `initial_planets`, `comets`, `comet_planet_ids`, `remainingOverageTime`
- Fleets die if they cross the sun or collide with planets during continuous motion
- Comets can be identified via `comet_planet_ids` and are removed before fleet launch when they expire
- Two-player games are created by running the environment with 2 agents; four-player games by running with 4 agents
