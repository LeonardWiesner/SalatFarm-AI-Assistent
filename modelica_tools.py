# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 14:16:35 2026

@author: subso
"""

from __future__ import annotations

import json
from pathlib import Path


MODEL_FILE = Path(
    r"C:\Users\subso\Desktop\VerticalFarming"
) / "VerticalFarming_v1.mo"


def search_modelica_code(
    query: str,
    context_lines: int = 8,
    max_results: int = 5,
) -> str:
    """
    Searches the Vertical Farming Modelica source code.

    Args:
        query:
            Component, parameter, variable or expression to search for.

        context_lines:
            Number of lines shown before and after a match.

        max_results:
            Maximum number of matching code excerpts.

    Returns:
        JSON containing matching code excerpts and line numbers.
    """

    if not query.strip():
        return json.dumps(
            {
                "status": "error",
                "message": "Die Suchanfrage ist leer.",
            },
            ensure_ascii=False,
        )

    source_lines = MODEL_FILE.read_text(
        encoding="utf-8",
    ).splitlines()

    query_lower = query.lower()
    matches: list[dict] = []

    for index, line in enumerate(source_lines):
        if query_lower not in line.lower():
            continue

        start = max(0, index - context_lines)
        end = min(
            len(source_lines),
            index + context_lines + 1,
        )

        excerpt = "\n".join(
            f"{line_number + 1}: {source_lines[line_number]}"
            for line_number in range(start, end)
        )

        matches.append(
            {
                "matching_line": index + 1,
                "excerpt": excerpt,
            }
        )

        if len(matches) >= max_results:
            break

    if not matches:
        return json.dumps(
            {
                "status": "success",
                "query": query,
                "matches": [],
                "message": "Keine passende Codezeile gefunden.",
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "status": "success",
            "query": query,
            "file": MODEL_FILE.name,
            "matches": matches,
        },
        ensure_ascii=False,
        indent=2,
    )