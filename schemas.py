# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 11:39:29 2026

@author: subso
"""

from typing import Literal

from pydantic import BaseModel, Field

class SimulationInput(BaseModel):
    """Validierte Eingabe für eine einzelne Vertical-Farm-Simulation."""

    PPFD: float = Field(
        default = 200,
        ge=0.0,
        le=750,
        description="Photosynthetic Photon Flux Density in mol/m^2/s",
    )

    photoperiod_h_per_day: float = Field(
        default = 16,
        ge=0.0,
        le=24.0,
        description="Lighting duration in h per day.",
    )

    simulation_duration_days: float = Field(
        default = 30,
        gt=0.0,
        le=120.0,
        description="Maximum simulationduration in days.",
    )

    number_of_plants: int = Field(
        default = 10,
        ge = 1,
        le = 10_000,
        description="Number of plants in the cultivation area.",
    )
    
    stop_at_harvest: bool = Field(
    default=True,
    description=(
        "Wenn true, beendet Modelica die Simulation "
        "beim Erreichen der Erntemasse."
        ),
    )
    
class SimulationResult(BaseModel):
    """Kompakte, für ein LLM geeignete Simulationausgabe."""

    status: Literal["success", "error"]

    PPFD: float
    photoperiod_h_per_day: float
    simulation_duration_days: float

    final_plant_mass_kg: float | None = None
    electrical_energy_kwh: float | None = None
    water_consumption_kg: float | None = None
    harvest_time_days: float | None = None
    specific_energy_kwh_per_kg: float | None = None

    harvest_reached: bool | None = None
    harvest_time_days: float | None = None

    message: str | None = None