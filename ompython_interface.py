# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 12:06:25 2026

@author: subso
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from OMPython import ModelicaSystem
from OMPython import OMCSessionZMQ
omc = OMCSessionZMQ()

omc.sendExpression('cd("C:/Users/wies_le/Desktop/VerticalFarming/Temp")')
MODEL_DIRECTORY = Path(
    r"C:\Users\subso\Desktop\VerticalFarming"
)

MODEL_FILE = MODEL_DIRECTORY / "VerticalFarming_v1.mo"
MODEL_NAME = "VerticalFarming_v1.Systemmodel"


class VerticalFarmSimulator:
    """Kapselt das Vertical-Farm-Modell und die OMPython-Kommunikation."""

    def __init__(
        self,
        model_file: Path = MODEL_FILE,
        model_name: str = MODEL_NAME,
    ) -> None:
        if not model_file.exists():
            raise FileNotFoundError(
                f"Modelica-Datei wurde nicht gefunden: {model_file}"
            )

        self.model = ModelicaSystem(
            str(model_file),
            model_name,
        )

    def get_available_parameters(self) -> dict[str, Any]:
        """Gibt alle über setParameters veränderbaren Parameter zurück."""
        return self.model.getParameters()

    def get_available_results(self) -> list[str]:
        """
        Gibt nach einer Simulation alle verfügbaren Ergebnisvariablen zurück.
        """
        return list(self.model.getSolutions())

    def simulate(
        self,
        parameters: dict[str, float],
        stop_time_s: float,
        result_variables: list[str],
    ) -> dict[str, NDArray[np.float64]]:
        """
        Setzt Modelica-Parameter, simuliert und gibt Zeitreihen zurück.

        Parameters
        ----------
        parameters:
            Modelica-Parameter mit vollständigem Namen, beispielsweise
            {"P_LED": 180.0, "photoperiod": 16.0}.

        stop_time_s:
            Simulationsdauer in Sekunden.

        result_variables:
            Ergebnisvariablen, beispielsweise
            ["plant.mPlant", "growLight.W_el"].
        """

        if stop_time_s <= 0:
            raise ValueError("stop_time_s muss größer als 0 sein.")

        if not result_variables:
            raise ValueError(
                "Es muss mindestens eine Ergebnisvariable angegeben werden."
            )

        parameter_assignments = [
            f"{name}={self._format_value(value)}"
            for name, value in parameters.items()
        ]

        if parameter_assignments:
            self.model.setParameters(parameter_assignments)

        self.model.setSimulationOptions(
            [
                "startTime=0",
                f"stopTime={stop_time_s}",
                "tolerance=1e-6",
            ]
        )

        try:
            self.model.simulate()
        except Exception as exc:
            raise RuntimeError(
                f"Die OpenModelica-Simulation ist fehlgeschlagen: {exc}"
            ) from exc

        requested_variables = ["time"]

        for variable in result_variables:
            if variable != "time":
                requested_variables.append(variable)

        try:
            raw_solutions = self.model.getSolutions(
                requested_variables
            )
        except Exception as exc:
            raise RuntimeError(
                "Die Simulation wurde ausgeführt, aber die Ergebnisse "
                f"konnten nicht gelesen werden: {exc}"
            ) from exc

        if len(raw_solutions) != len(requested_variables):
            raise RuntimeError(
                "Die Anzahl der zurückgegebenen Ergebnisreihen stimmt "
                "nicht mit der Anzahl der angefragten Variablen überein."
            )

        solutions: dict[str, NDArray[np.float64]] = {}

        for name, values in zip(
            requested_variables,
            raw_solutions,
            strict=True,
        ):
            array = np.asarray(values, dtype=float)

            if array.size == 0:
                raise RuntimeError(
                    f"Die Ergebnisvariable '{name}' enthält keine Werte."
                )

            solutions[name] = array

        number_of_time_points = solutions["time"].size

        for name, values in solutions.items():
            if values.size != number_of_time_points:
                raise RuntimeError(
                    f"Die Ergebnisvariable '{name}' hat {values.size} "
                    f"Werte, erwartet wurden {number_of_time_points}."
                )

        return solutions

    @staticmethod
    def _format_value(value: float | int | bool) -> str:
        """Formatiert Python-Werte für Modelica-Parameterzuweisungen."""

        if isinstance(value, bool):
            return "true" if value else "false"

        if not isinstance(value, (int, float)):
            raise TypeError(
                f"Nicht unterstützter Parametertyp: {type(value).__name__}"
            )

        if not np.isfinite(value):
            raise ValueError(
                f"Parameterwert muss endlich sein, erhalten: {value}"
            )

        return repr(value)


# Das Modell wird beim Import einmal geladen und übersetzt.
simulator = VerticalFarmSimulator()