# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 16:18:45 2026

@author: subso
"""

from __future__ import annotations

import json
from typing import Any

from ollama import ChatResponse, chat

from simulation_tool import run_vertical_farm_simulation

from modelica_tools import search_modelica_code

from visualization_tool import request_simulation_plot


MODEL_NAME = "qwen3:4b"

SYSTEM_PROMPT = """
Du bist ein technischer Simulationsassistent für ein
Modelica-basiertes Vertical-Farming-Modell.

1. Verwende run_vertical_farm_simulation für Simulationen.

2. request_simulation_plot
   Fordert die grafische Darstellung von Zeitreihen aus der
   letzten Simulation an. Verfügbare Diagrammgrößen sind:
   plant_mass, electrical_energy und water_consumption.

3. Verwende search_modelica_code, wenn der Nutzer nach Komponenten,
   Gleichungen, Parametern, Variablen oder der Implementierung des
   Modelica-Modells fragt.

Deine Aufgaben:
- Erkenne Simulationsanfragen des Nutzers.
- Verwende für reale Simulationen ausschließlich das bereitgestellte Tool.
- Erfinde niemals Simulationsergebnisse.
- Verwende request_simulation_plot, wenn der Nutzer ausdrücklich
  nach einem Diagramm, Graphen, Verlauf oder einer grafischen
  Darstellung fragt.
- Gib bei allen technischen Größen Einheiten an.
- Wenn der Nutzer nur einen Parameter verändert, übernimm die übrigen
  Parameter aus der vorherigen Simulationsanfrage.
- Nenne bei einer neuen Simulation alle tatsächlich verwendeten Parameter.
- Unterscheide zwischen Simulationsergebnis und Interpretation.
- Verwende 30 Tage Simulationsdauer, wenn keine Dauer genannt wird.
- PPFD wird in µmol/(m² s) angegeben.
- Die Photoperiode wird in Stunden pro Tag angegeben.
- Mit der Abfrage stop_at_harvest kann die Simulation bei Erreichen der Erntmasse abgebrochen werden
- Weise auf fehlende oder unplausible Angaben hin.
"""


AVAILABLE_TOOLS = {
    "run_vertical_farm_simulation":
        run_vertical_farm_simulation,

    "search_modelica_code":
        search_modelica_code,
        
     "request_simulation_plot":
        request_simulation_plot,
}


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """Führt ausschließlich freigegebene Python-Tools aus."""

    function = AVAILABLE_TOOLS.get(tool_name)

    if function is None:
        return json.dumps(
            {
                "status": "error",
                "message": f"Unbekanntes Tool: {tool_name}",
            },
            ensure_ascii=False,
        )

    try:
        return function(**arguments)

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": f"Tool-Ausführung fehlgeschlagen: {exc}",
            },
            ensure_ascii=False,
        )


def ask_vertical_farm_assistant(
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict:
    """
    Verarbeitet eine Nutzeranfrage und erlaubt dem lokalen LLM,
    die Modelica-Simulation aufzurufen.
    """

    messages: list[Any] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]
    
    ui_actions: list[dict] = []
    

    for _ in range(5):
        response: ChatResponse = chat(
            model=MODEL_NAME,
            messages=messages,
            tools=[
                run_vertical_farm_simulation,
                search_modelica_code,
                request_simulation_plot,
            ],
            think=False,
            options={
                "num_ctx": 4096,
                "temperature": 0.1,
            },
        )
    
        messages.append(response.message)
    
        tool_calls = response.message.tool_calls or []
    
        if not tool_calls:
            return {
                "answer": (
                    response.message.content
                    or "Das Modell hat keine finale Antwort erzeugt."
                ),
                "ui_actions": ui_actions,
            }
    
        # Berechnungstools zuerst ausführen.
        # Dadurch wird nicht versehentlich die vorherige Simulation geplottet,
        # falls das Modell Simulation und Plot gleichzeitig anfordert.
        ordered_tool_calls = sorted(
            tool_calls,
            key=lambda call: (
                1
                if call.function.name
                == "request_simulation_plot"
                else 0
            ),
        )
    
        for tool_call in ordered_tool_calls:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments
    
            print("\n--- TOOL-AUFRUF ---")
            print("Tool:", tool_name)
            print("Argumente:", arguments)
    
            tool_result = execute_tool(
                tool_name=tool_name,
                arguments=arguments,
            )
    
            try:
                parsed_result = json.loads(tool_result)
    
                if (
                    parsed_result.get("status") == "success"
                    and parsed_result.get("ui_action")
                    == "show_simulation_plot"
                ):
                    ui_actions.append(parsed_result)
    
            except json.JSONDecodeError:
                pass
    
            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": tool_result,
                }
            )
    
    return {
        "answer": (
            "Die maximale Anzahl an Tool-Aufrufen "
            "wurde erreicht."
        ),
        "ui_actions": ui_actions,
    }

    return (
        "Die maximale Anzahl an Tool-Aufrufen wurde erreicht. "
        "Möglicherweise konnte das Modell die Anfrage nicht "
        "eindeutig verarbeiten."
    )


if __name__ == "__main__":
    question = (
        "Simuliere Salat bei einer PPFD von 200 µmol/(m² s), "
        "einer Photoperiode von 16 Stunden und einer "
        "Simulationsdauer von 30 Tagen."
    )

    answer = ask_vertical_farm_assistant(question)

    print("\nAntwort des Assistenten:\n")
    print(answer)