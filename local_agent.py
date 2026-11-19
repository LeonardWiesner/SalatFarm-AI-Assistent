# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 16:18:45 2026

@author: subso
"""

from __future__ import annotations

import json
from inspect import signature
from typing import Any

from ollama import ChatResponse, chat

from simulation_tool import run_vertical_farm_simulation, get_last_simulation_series

from modelica_tools import search_modelica_code

from visualization_tool import request_simulation_plot, build_simulation_plot_request


MODEL_NAME = "qwen2.5:3b"
MAX_HISTORY_TURNS = 6

# Alle Felder sind optional: fehlend bedeutet bisherigen Wert übernehmen.
SIMULATION_TOOL = {
    "type": "function",
    "function": {
        "name": "run_vertical_farm_simulation",
        "description": (
            "Simuliert die Vertical Farm. Übergib nur vom Nutzer ausdrücklich "
            "angegebene oder geänderte Parameter. Python ergänzt fehlende Werte "
            "aus der letzten erfolgreichen Konfiguration, sonst aus Standardwerten."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "PPFD": {"type": "number", "description": "PPFD in µmol/(m² s), 0 bis 750."},
                "photoperiod_h_per_day": {"type": "number", "description": "Beleuchtungsdauer in h/d, 0 bis 24."},
                "simulation_duration_days": {"type": "number", "description": "Maximale Dauer in Tagen, größer 0 bis 120."},
                "number_of_plants": {"type": "integer", "description": "Pflanzenanzahl, 1 bis 10000."},
                "stop_at_harvest": {"type": "boolean", "description": "Bei Erntereife abbrechen."},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
}


def default_simulation_parameters() -> dict[str, Any]:
    """Verwendet dieselben Standardwerte wie das Simulationstool."""
    return {
        name: parameter.default
        for name, parameter in signature(run_vertical_farm_simulation).parameters.items()
    }


def recent_conversation(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Behält die letzten sechs Nutzeranfragen samt zugehörigen Antworten."""
    messages = [
        {"role": message["role"], "content": message["content"]}
        for message in history
        if message.get("role") in {"user", "assistant"}
        and isinstance(message.get("content"), str)
    ]
    user_indices = [i for i, message in enumerate(messages) if message["role"] == "user"]
    if not user_indices:
        return []
    start = user_indices[max(0, len(user_indices) - MAX_HISTORY_TURNS)]
    return messages[start:]

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
  Parameter nicht selbst in den Tool-Aufruf. Übergib nur ausdrücklich
  genannte Änderungen; Python ergänzt die übrigen Parameter.
- Nenne bei einer neuen Simulation alle tatsächlich verwendeten Parameter.
- Unterscheide zwischen Simulationsergebnis und Interpretation.
- Bezeichne requested_parameters.simulation_duration_days als maximale Dauer
  und simulation_duration_days im Ergebnis als tatsächliche Laufzeit bis zum Ende.
- Ohne bisherige Konfiguration gilt eine maximale Simulationsdauer von 30 Tagen.
- Der aktuelle Python-Sitzungszustand ist für Konfiguration und letztes Ergebnis
  maßgeblich. Ältere Chatnachrichten können frühere Konfigurationen enthalten.
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
    agent_state: dict[str, Any] | None = None,
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
        if tool_name == "run_vertical_farm_simulation":
            state = agent_state if agent_state is not None else {}
            parameters = {
                **default_simulation_parameters(),
                **state.get("simulation_parameters", {}),
                **arguments,
            }
            result = json.loads(function(**parameters))
            result["requested_parameters"] = parameters
            if result.get("status") == "success":
                # Die angeforderte Dauer bleibt auch bei vorzeitiger Ernte erhalten.
                state.update(
                    simulation_parameters=parameters,
                    last_simulation_result=result,
                    simulation_series=get_last_simulation_series(),
                )
            return json.dumps(result, ensure_ascii=False)
        if tool_name == "request_simulation_plot" and agent_state is not None:
            return build_simulation_plot_request(
                **arguments,
                has_simulation=bool(agent_state.get("simulation_series")),
            )
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
    agent_state: dict[str, Any] | None = None,
) -> dict:
    """
    Verarbeitet eine Nutzeranfrage und erlaubt dem lokalen LLM,
    die Modelica-Simulation aufzurufen.
    """

    state = agent_state if agent_state is not None else {}
    session_context = {
        "simulation_parameters": state.get(
            "simulation_parameters", default_simulation_parameters()
        ),
        "last_simulation_result": state.get("last_simulation_result"),
    }
    messages: list[Any] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\nAktueller Python-Sitzungszustand:\n"
            + json.dumps(session_context, ensure_ascii=False),
        },
        *recent_conversation(conversation_history or []),
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
                SIMULATION_TOOL,
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
                agent_state=state,
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

if __name__ == "__main__":
    question = (
        "Simuliere Salat bei einer PPFD von 200 µmol/(m² s), "
        "einer Photoperiode von 16 Stunden und einer "
        "Simulationsdauer von 30 Tagen."
    )

    answer = ask_vertical_farm_assistant(question)

    print("\nAntwort des Assistenten:\n")
    print(answer)
