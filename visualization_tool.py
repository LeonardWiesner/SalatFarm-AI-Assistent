# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 11:27:43 2026

@author: subso
"""

import json

from simulation_tool import get_last_simulation_series


ALLOWED_PLOT_VARIABLES = {
    "plant_mass",
    "electrical_energy",
    "water_consumption",
}


def request_simulation_plot(
    variables: list[str],
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

    available_series = get_last_simulation_series()

    if not available_series:
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

    valid_variables = [
        variable
        for variable in variables
        if variable in ALLOWED_PLOT_VARIABLES
    ]

    # Doppelte Variablen entfernen und Reihenfolge beibehalten.
    valid_variables = list(
        dict.fromkeys(valid_variables)
    )

    invalid_variables = [
        variable
        for variable in variables
        if variable not in ALLOWED_PLOT_VARIABLES
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