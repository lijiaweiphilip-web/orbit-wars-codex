# Forced-Mission Trace Diff Parser Test

{
  "checks": {
    "arrival_event": true,
    "fleet_count": true,
    "owner_change": true,
    "source_ships": true,
    "target_ships": true
  },
  "diff": {
    "arrival_event": true,
    "fleet_count": 1,
    "leader_enemy_strength": -11.0,
    "owner_change": true,
    "planet_count": 1.0,
    "production": 6.0,
    "rank": 0.0,
    "ship_total": 18.0,
    "source_ships": {
      "1": -42.0
    },
    "target_owner": -1,
    "target_ships": -27.0,
    "top2": 0.0,
    "win_proxy": 0.0
  },
  "required_fields": [
    "source_ships",
    "target_ships",
    "fleet_count",
    "arrival_event",
    "owner_change"
  ],
  "status": "PASS"
}
