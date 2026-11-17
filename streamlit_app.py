# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 14:41:58 2026

@author: subso
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import math

import re

import streamlit as st

from local_agent import ask_vertical_farm_assistant

from simulation_tool import get_last_simulation_series


st.set_page_config(
    page_title="Vertical Farm Engineering Assistant",
    page_icon="🌱",
    layout="wide",
)

PLOT_CONFIG = {
    "plant_mass": {
        "series_key": "plant_mass_kg",
        "title": "Pflanzenmasse",
        "value_label": "Pflanzenmasse [kg]",
    },
    "electrical_energy": {
        "series_key": "electrical_energy_kwh",
        "title": "Elektrischer Energieverbrauch",
        "value_label": "Elektrische Energie [kWh]",
    },
    "water_consumption": {
        "series_key": "water_consumption_kg",
        "title": "Wasserverbrauch",
        "value_label": "Wasserverbrauch [kg]",
    },
}

def downsample_series(
    time_values: np.ndarray,
    result_values: np.ndarray,
    maximum_points: int = 500,
) -> tuple[list[float], list[float]]:
    """
    Reduces long time series while preserving the first
    and final simulation points.
    """

    number_of_points = len(time_values)

    if number_of_points <= maximum_points:
        return (
            time_values.tolist(),
            result_values.tolist(),
        )

    step = math.ceil(
        number_of_points / maximum_points
    )

    indices = list(
        range(0, number_of_points, step)
    )

    if indices[-1] != number_of_points - 1:
        indices.append(number_of_points - 1)

    return (
        time_values[indices].tolist(),
        result_values[indices].tolist(),
    )

def build_plot_payloads(
    ui_actions: list[dict],
) -> list[dict]:
    """
    Creates persistent plot data from LLM UI instructions.
    """

    series = get_last_simulation_series()

    if not series:
        return []

    time_days = np.asarray(
        series["time_days"],
        dtype=float,
    )

    plot_payloads: list[dict] = []

    requested_variables: list[str] = []

    for action in ui_actions:
        if (
            action.get("ui_action")
            != "show_simulation_plot"
        ):
            continue

        requested_variables.extend(
            action.get("variables", [])
        )

    requested_variables = list(
        dict.fromkeys(requested_variables)
    )

    for variable in requested_variables:
        config = PLOT_CONFIG.get(variable)

        if config is None:
            continue

        series_key = config["series_key"]

        if series_key not in series:
            continue

        values = np.asarray(
            series[series_key],
            dtype=float,
        )

        if len(values) != len(time_days):
            continue

        plot_time, plot_values = downsample_series(
            time_values=time_days,
            result_values=values,
        )

        plot_payloads.append(
            {
                "variable": variable,
                "title": config["title"],
                "value_label": config["value_label"],
                "time_days": plot_time,
                "values": plot_values,
            }
        )

    return plot_payloads

def render_plot_payloads(
    plot_payloads: list[dict],
) -> None:
    """
    Stellt die vom LLM angeforderten Simulationsverläufe
    mit sichtbaren Datenpunkten und beschrifteten Achsen dar.
    """

    for plot in plot_payloads:
        time_days = np.asarray(
            plot["time_days"],
            dtype=float,
        )

        values = np.asarray(
            plot["values"],
            dtype=float,
        )

        if len(time_days) != len(values):
            st.warning(
                f"Das Diagramm '{plot['title']}' konnte nicht "
                "dargestellt werden, da Zeit- und Ergebnisarray "
                "unterschiedlich lang sind."
            )
            continue

        chart_data = pd.DataFrame(
            {
                "time_days": time_days,
                "value": values,
            }
        )

        # Unendliche und ungültige Werte entfernen.
        chart_data = chart_data.replace(
            [np.inf, -np.inf],
            np.nan,
        ).dropna()

        # Modelica kann bei Ereignissen mehrere Werte mit demselben
        # Zeitstempel speichern.
        chart_data = chart_data.drop_duplicates(
            subset="time_days",
            keep="last",
        )

        chart_data = chart_data.sort_values(
            by="time_days"
        )

        if chart_data.empty:
            st.warning(
                f"Für '{plot['title']}' sind keine gültigen "
                "Datenpunkte verfügbar."
            )
            continue

        st.subheader(plot["title"])

        chart = (
            alt.Chart(chart_data)
            .mark_line(
                point=alt.OverlayMarkDef(
                    size=45,
                ),
                strokeWidth=2,
            )
            .encode(
                x=alt.X(
                    "time_days:Q",
                    title="Zeit [Tage]",
                    axis=alt.Axis(
                        grid=True,
                        format=".1f",
                    ),
                ),
                y=alt.Y(
                    "value:Q",
                    title=plot["value_label"],
                    axis=alt.Axis(
                        grid=True,
                    ),
                    scale=alt.Scale(
                        zero=False,
                    ),
                ),
                tooltip=[
                    alt.Tooltip(
                        "time_days:Q",
                        title="Zeit [Tage]",
                        format=".3f",
                    ),
                    alt.Tooltip(
                        "value:Q",
                        title=plot["value_label"],
                        format=".4f",
                    ),
                ],
            )
            .properties(
                height=380,
            )
            .interactive()
        )

        st.altair_chart(
            chart,
            width="stretch",
        )

        st.caption(
            f"{len(chart_data)} dargestellte Datenpunkte"
        )

def remove_thinking_trace(text: str) -> str:
    """
    Entfernt versehentlich ausgegebene Qwen-Thinking-Blöcke.

    Normalerweise sollte local_agent.py bereits nur den finalen
    Antworttext zurückgeben. Diese Funktion dient als zusätzliche
    Absicherung für <think>...</think>-Ausgaben.
    """

    if not text:
        return "Das Modell hat keine Antwort erzeugt."

    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Absicherung für unvollständig übertragene Thinking-Blöcke
    if "</think>" in cleaned.lower():
        cleaned = re.split(
            r"</think>",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[-1]

    return cleaned.strip()


def initialize_session_state() -> None:
    """Initialisiert den Chatverlauf für die aktuelle Browsersitzung."""

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hallo! Ich kann dein Modelica-Vertical-Farm-Modell "
                    "über OMPython simulieren. Gib beispielsweise eine "
                    "PPFD [µmol/(m² s)], Photoperiode [h] und Simulationsdauer [days] an."
                ),
            }
        ]

    if "simulation_running" not in st.session_state:
        st.session_state.simulation_running = False


def clear_chat() -> None:
    """Setzt den sichtbaren Chatverlauf zurück."""

    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Der Chat wurde zurückgesetzt. Welche Konfiguration "
                "soll ich simulieren?"
            ),
        }
    ]


initialize_session_state()


# ---------------------------------------------------------
# Kopfbereich
# ---------------------------------------------------------

st.title("🌱 Vertical Farm Engineering Assistant")

st.caption(
    "Lokales LLM mit Ollama · Modelica-Simulation über OMPython"
)


# ---------------------------------------------------------
# Seitenleiste
# ---------------------------------------------------------

with st.sidebar:
    st.header("Modell")

    st.write("**LLM:** Qwen3 4B")
    st.write("**Simulation:** OpenModelica")
    st.write("**Schnittstelle:** OMPython")

    st.divider()

    st.subheader("Beispielanfragen")

    st.code(
        "Wie wird der Parameter mPlant der Pflanzennmasse berechnet? "
        ,
        language=None,
    )
    st.code(
        "Brich die Simulation mit einer PPFD 200, 15 Pflanzen, 16h Photoperiode bei Erreichen der Erntemasse ab. "
        ,
        language=None,
    )

    st.code(
        "Wie groß ist der Energiebedarf bei einer PPFD von 250, 15 Pflanzen "
        "und 18 Stunden Beleuchtung über 25 Tage?",
        language=None,
    )

    st.divider()

    st.button(
        "Chat zurücksetzen",
        on_click=clear_chat,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Bisherigen Chatverlauf darstellen
# ---------------------------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        render_plot_payloads(
            message.get("plots", [])
        )


# ---------------------------------------------------------
# Neue Nutzeranfrage
# ---------------------------------------------------------

prompt = st.chat_input(
    "Zum Beispiel: Simuliere PPFD 200, 20 Pflanzen bei einer Photoperiode von 16 h/d.",
    disabled=st.session_state.simulation_running,
)

if prompt:
    # Verlauf kopieren, bevor der aktuelle Prompt ergänzt wird.
    history_for_llm = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in st.session_state.messages
        if message["role"] in {"user", "assistant"}
    ]

    # Aktuelle Nutzernachricht sichtbar speichern.
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.simulation_running = True

    with st.chat_message("assistant"):
        try:
            with st.spinner(
                "Anfrage wird verarbeitet und das "
                "Modelica-Modell gegebenenfalls simuliert …",
                show_time=True,
            ):
                agent_result = (
                    ask_vertical_farm_assistant(
                        user_message=prompt,
                        conversation_history=(
                            history_for_llm
                        ),
                    )
                )
    
            answer = remove_thinking_trace(
                agent_result["answer"]
            )
    
            plot_payloads = build_plot_payloads(
                agent_result.get(
                    "ui_actions",
                    [],
                )
            )
    
            st.markdown(answer)
    
            render_plot_payloads(
                plot_payloads
            )
    
        except Exception as exc:
            answer = (
                "Die Anfrage konnte nicht verarbeitet "
                "werden.\n\n"
                f"**Fehler:** "
                f"`{type(exc).__name__}: {exc}`"
            )
    
            plot_payloads = []
    
            st.error(answer)
    
        finally:
            st.session_state.simulation_running = False
    
    
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "plots": plot_payloads,
        }
    )
    