# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 11:27:43 2026

@author: subso
"""

import json
from typing import Literal

from simulation_tool import get_last_simulation_series


ALLOWED_PLOT_VARIABLES = {
    "plant_mass",
    "electrical_energy",
    "water_consumption",
}


def request_simulation_plot(
    variables: list[Literal["plant_mass", "electrical_energy", "water_consumption"]],
) -> str:
    """
    Fordert Diagramme aus der zuletzt ausgeführten Simulation an.

    Verwende dieses Tool, wenn der Nutzer ausdrücklich nach einem
    Diagramm, Graphen, zeitlichen Verlauf oder einer grafischen
    Darstellung fragt.

    Args:
        variables:
            Liste der darzustellenden Simulationsgrößen.

            Erlaubte Werte:

            - plant_mass:
              Pflanzenmasse über der Simulationszeit in kg.

            - electrical_energy:
              Kumulierter elektrischer Energieverbrauch über der
              Simulationszeit in kWh.

            - water_consumption:
              Kumulierter Wasserverbrauch über der
              Simulationszeit in kg.

    Returns:
        JSON-Anweisung für die Streamlit-Benutzeroberfläche.
        Die Funktion erstellt selbst kein Diagramm.
    """

    return build_simulation_plot_request(
        variables, has_simulation=bool(get_last_simulation_series())
    )


def build_simulation_plot_request(variables: list[str], has_simulation: bool) -> str:
    """Validiert eine Diagrammanfrage gegen die Daten der jeweiligen Sitzung."""

    if not has_simulation:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "Es sind noch keine Zeitreihen einer "
                    "erfolgreichen Simulation verfügbar."
                ),
            },
            ensure_ascii=False,
        )

    if not isinstance(variables, list):
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "Die Diagrammvariablen müssen als Liste "
                    "übergeben werden."
                ),
            },
            ensure_ascii=False,
        )

    # Kleine Modelle verwenden gelegentlich die Ergebnisnamen samt Einheit.
    # Dieselben Größen werden auf die Bezeichner der Oberfläche abgebildet.
    result_names = {
        "plant_mass_kg": "plant_mass",
        "final_plant_mass_kg": "plant_mass",
        "electrical_energy_kwh": "electrical_energy",
        "water_consumption_kg": "water_consumption",
    }
    variables = [
        result_names.get(variable, variable) if isinstance(variable, str) else variable
        for variable in variables
    ]
    valid_variables = [
        variable
        for variable in variables
        if isinstance(variable, str) and variable in ALLOWED_PLOT_VARIABLES
    ]

    # Doppelte Variablen entfernen und Reihenfolge beibehalten.
    valid_variables = list(
        dict.fromkeys(valid_variables)
    )

    invalid_variables = [
        variable
        for variable in variables
        if not isinstance(variable, str) or variable not in ALLOWED_PLOT_VARIABLES
    ]

    if not valid_variables:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "Es wurde keine gültige Diagrammvariable "
                    "angegeben."
                ),
                "allowed_variables": sorted(
                    ALLOWED_PLOT_VARIABLES
                ),
                "invalid_variables": invalid_variables,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "success",
            "ui_action": "show_simulation_plot",
            "variables": valid_variables,
            "ignored_variables": invalid_variables,
        },
        ensure_ascii=False,
    )
