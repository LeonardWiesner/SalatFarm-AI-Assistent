# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 11:50:05 2026

@author: subso
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

import numpy as np
from numpy.typing import NDArray

from ompython_interface import simulator
from schemas import SimulationInput, SimulationResult


_LAST_SIMULATION_SERIES: dict[
    str,
    NDArray[np.float64],
] = {}

logger = logging.getLogger(__name__)

SECONDS_PER_DAY = 86_400.0
JOULES_PER_KWH = 3_600_000.0

# Linke Seite: Namen für Python und später das LLM.
# Rechte Seite: tatsächliche Namen der Modelica-Parameter.
MODEL_PARAMETER_MAP = {
    "PPFD": "PPFD_set",
    "photoperiod_h_per_day": "photoperiod_set",
    "number_of_plants": "nPlants",
    "stop_at_harvest": "stopAtHarvest"
}


# Tatsächliche Ergebnisvariablen aus deinem Modelica-Modell.
MODEL_RESULT_MAP = {
    "plant_mass": "plantunit.mPlant",
    "electrical_energy": "lettuceLight.W_el",
    "mWater": "tank.mWater",
    "harvest_ready":"plantunit.harvestReady"
}


def run_vertical_farm_simulation(
    PPFD: float = 200,
    photoperiod_h_per_day: float = 16,
    simulation_duration_days: float = 30,
    number_of_plants: int = 10,
    stop_at_harvest: bool = True,
) -> str:
    """
    Führt eine validierte Vertical-Farm-Simulation aus.

    Führt eine Modelica-Simulation einer Vertical Farm durch.

    Args:
        PPFD:
            Photosynthetische Photonenflussdichte in µmol/(m² s).
            Zulässiger Bereich: 0 bis 750.

        photoperiod_h_per_day:
            Tägliche Beleuchtungsdauer in Stunden pro Tag.
            Zulässiger Bereich: 0 bis 24.

        simulation_duration_days:
            Simulationsdauer in Tagen. Standardwert: 30 Tage.
            
        number_of_plants:
            Anzahl der Pflanzen. Standardwert: 10 Pflanzen.
            
        stop_at_harvest:
            Beendet die Simulation beim Erreichen der Erntemasse.
            Standardwert ist Richtig, was einen Abbruch der Simulation zur Folge hat.

    Returns:
        JSON-String mit Pflanzenmasse, elektrischer Energie,
        Wasserverbrauch und spezifischem Energiebedarf.
    """

    try:
        request = SimulationInput(
            PPFD=PPFD,
            photoperiod_h_per_day=photoperiod_h_per_day,
            simulation_duration_days=simulation_duration_days,
            number_of_plants=number_of_plants,
            stop_at_harvest=stop_at_harvest
        )

    except ValidationError as exc:
        return SimulationResult(
            status="error",
            PPFD=PPFD,
            photoperiod_h_per_day=photoperiod_h_per_day,
            simulation_duration_days=simulation_duration_days,
            number_of_plants=number_of_plants,
            stop_at_harvest=stop_at_harvest,
            message=f"Ungültige Simulationsparameter: {exc}",
        ).model_dump_json(indent=2)

    modelica_parameters = {
        MODEL_PARAMETER_MAP["PPFD"]:
            request.PPFD *1e-6,

        MODEL_PARAMETER_MAP["photoperiod_h_per_day"]:
            request.photoperiod_h_per_day*3600,
            
        MODEL_PARAMETER_MAP["number_of_plants"]:
            request.number_of_plants,
            
        MODEL_PARAMETER_MAP["stop_at_harvest"]:
            request.stop_at_harvest
    }

    result_variables = list(MODEL_RESULT_MAP.values())

    stop_time_s = (
        request.simulation_duration_days
        * SECONDS_PER_DAY
    )

    try:
        solutions = simulator.simulate(
            parameters=modelica_parameters,
            stop_time_s=stop_time_s,
            result_variables=result_variables,
        )

        plant_mass = solutions[
            MODEL_RESULT_MAP["plant_mass"]
        ]

        electrical_energy = solutions[
            MODEL_RESULT_MAP["electrical_energy"]
        ]

        mWater = solutions[
            MODEL_RESULT_MAP["mWater"]
        ]
        
        time_s = solutions["time"]
        
        
        harvest_ready = solutions[
            MODEL_RESULT_MAP["harvest_ready"]
        ]
        
        _LAST_SIMULATION_SERIES.clear()

        _LAST_SIMULATION_SERIES.update(
            {
                "time_days":
                    time_s / SECONDS_PER_DAY,
        
                "plant_mass_kg":
                    plant_mass,
        
                "electrical_energy_kwh":
                    (
                        electrical_energy
                        - electrical_energy[0]
                    ) / JOULES_PER_KWH,
        
                "water_consumption_kg":
                    mWater[0] - mWater,
            }
        )



        initial_plant_mass_kg = float(plant_mass[0])
        final_plant_mass_kg = float(plant_mass[-1])

        biomass_growth_kg = (
            final_plant_mass_kg
            - initial_plant_mass_kg
        )

        # W_el wird als integrierte Energie in Joule angenommen.
        electrical_energy_j = (
            float(electrical_energy[-1])
            - float(electrical_energy[0])
        )

        electrical_energy_kwh = (
            electrical_energy_j
            / JOULES_PER_KWH
        )

        mWater_kg = (
       
             float(mWater[0])-float(mWater[-1])
        )
        
        # Tatsächlicher Endzeitpunkt – egal, ob durch terminate()
        # oder durch Erreichen der maximalen Simulationsdauer.
        actual_simulation_duration_days = (
           float(time_s[-1])
           / SECONDS_PER_DAY
       )
        
        harvest_reached = (
            float(harvest_ready[-1]) > 0.5
        )
        
        harvest_time_days = (
           actual_simulation_duration_days
           if harvest_reached
           else None
       )

        specific_energy = None

        if biomass_growth_kg > 0:
            specific_energy = (
                electrical_energy_kwh
                / biomass_growth_kg
            )

        result = SimulationResult(
            status="success",
            PPFD=request.PPFD,
            photoperiod_h_per_day=(
                request.photoperiod_h_per_day
            ),
            simulation_duration_days=(
                actual_simulation_duration_days
            ),
            number_of_plants=request.number_of_plants,
            stop_at_harvest=request.stop_at_harvest,
            
            initial_plant_mass_kg=initial_plant_mass_kg,
            final_plant_mass_kg=final_plant_mass_kg,
            biomass_growth_kg=biomass_growth_kg,
            electrical_energy_kwh=electrical_energy_kwh,
            water_consumption_kg=mWater_kg,
            specific_energy_kwh_per_kg=specific_energy,
            harvest_reached=harvest_reached,
            harvest_time_days=harvest_time_days,
            message=(
            None
            if harvest_reached or not request.stop_at_harvest
            else (
                "Die Erntemasse wurde innerhalb der maximalen "
                "Simulationsdauer nicht erreicht."
            )
        ),
        )

        logger.info(
            "Vertical-Farm-Simulation erfolgreich: %s",
            result.model_dump(),
        )

        return result.model_dump_json(indent=2)

    except Exception as exc:
        logger.exception(
            "Vertical-Farm-Simulation fehlgeschlagen."
        )

        return SimulationResult(
            status="error",
            PPFD=request.PPFD,
            photoperiod_h_per_day=(
                request.photoperiod_h_per_day
            ),
            simulation_duration_days=(
                request.simulation_duration_days
            ),
            number_of_plants=request.number_of_plants,
            stop_at_harvest=request.stop_at_harvest,
            message=f"Simulation fehlgeschlagen: {exc}",
        ).model_dump_json(indent=2)
    
def get_last_simulation_series(
    ) -> dict[str, NDArray[np.float64]]:
        """
        Returns copies of all time series from the most recent
        successful Vertical Farm simulation.
        """
    
        return {
            name: values.copy()
            for name, values
            in _LAST_SIMULATION_SERIES.items()
        }