from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanetState:
    id: int
    owner: int
    x: float
    y: float
    radius: float
    ships: int
    production: int
    is_comet: bool = False


@dataclass(frozen=True)
class FleetState:
    id: int
    owner: int
    x: float
    y: float
    angle: float
    from_planet_id: int
    ships: int


@dataclass(frozen=True)
class GameState:
    step: int
    my_id: int
    num_players: int
    planets: list[PlanetState]
    fleets: list[FleetState]
    angular_velocity: float
    episode_steps: int
    comet_planet_ids: set[int]
    raw_observation: dict[str, Any]

    @property
    def my_planets(self) -> list[PlanetState]:
        return [planet for planet in self.planets if planet.owner == self.my_id]

    @property
    def enemy_planets(self) -> list[PlanetState]:
        return [planet for planet in self.planets if planet.owner not in (-1, self.my_id)]

    @property
    def neutral_planets(self) -> list[PlanetState]:
        return [planet for planet in self.planets if planet.owner == -1]


def parse_observation(observation: dict[str, Any], configuration: dict[str, Any]) -> GameState:
    comet_planet_ids = set(observation.get("comet_planet_ids", []))
    planets = [
        PlanetState(
            id=int(raw[0]),
            owner=int(raw[1]),
            x=float(raw[2]),
            y=float(raw[3]),
            radius=float(raw[4]),
            ships=int(raw[5]),
            production=int(raw[6]),
            is_comet=int(raw[0]) in comet_planet_ids,
        )
        for raw in observation.get("planets", [])
    ]
    fleets = [
        FleetState(
            id=int(raw[0]),
            owner=int(raw[1]),
            x=float(raw[2]),
            y=float(raw[3]),
            angle=float(raw[4]),
            from_planet_id=int(raw[5]),
            ships=int(raw[6]),
        )
        for raw in observation.get("fleets", [])
    ]
    player_ids = {planet.owner for planet in planets if planet.owner >= 0}
    player_ids.update(fleet.owner for fleet in fleets if fleet.owner >= 0)
    my_id = int(observation.get("player", 0))
    player_ids.add(my_id)
    return GameState(
        step=int(observation.get("step", 0)),
        my_id=my_id,
        num_players=max(len(player_ids), 2),
        planets=planets,
        fleets=fleets,
        angular_velocity=float(observation.get("angular_velocity", 0.0)),
        episode_steps=int(configuration.get("episodeSteps", 500)),
        comet_planet_ids=comet_planet_ids,
        raw_observation=observation,
    )
