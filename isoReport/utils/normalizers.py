"""
Normalización de claves y parseo de fórmulas.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def normalize_numero_solicitud_for_match(value: Any) -> str:
    """Valor canónico para comparar numero_solicitud (1, '1', 1.0 -> '1')."""
    if value is None:
        return ""
    s = str(value).strip()
    try:
        n = int(float(s))
        return str(n)
    except (ValueError, TypeError):
        return s


def numero_solicitud_canonico(value: Any, year: int | None = None) -> str:
    """
    Extrae el número de solicitud canónico.
    - "24/2025" o "01/2025" -> parte izquierda como entero -> "24", "1"
    - 1, "1", 1.0 -> "1"
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if "/" in s:
        part = s.split("/", 1)[0].strip()
        try:
            n = int(float(part))
            return str(n)
        except (ValueError, TypeError):
            return part or ""
    return normalize_numero_solicitud_for_match(value)


def parse_pasted_formula(text: str) -> List[Dict[str, str]]:
    """
    Parsea texto pegado (TAB o ; como separador) en filas de fórmula.
    Cada línea: materia_prima, porcentaje_peso (si falta %, se deja vacío).
    """
    rows: List[Dict[str, str]] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t", 1)]
        elif ";" in line:
            parts = [p.strip() for p in line.split(";", 1)]
        else:
            parts = [line.strip(), ""]
        materia = parts[0] if len(parts) > 0 else ""
        pct = parts[1] if len(parts) > 1 else ""
        rows.append({"materia_prima": materia, "porcentaje_peso": pct})
    return rows


_PESO_PATTERN = re.compile(r"^\s*-?\d+([,.]\d+)?\s*$")


def validate_peso(value: str) -> Tuple[bool, str]:
    """
    Valida que value sea un número aceptable (coma o punto como decimal).
    Devuelve (True, "") si es válido, (False, mensaje_error) si no.
    """
    if value is None:
        return True, ""
    s = str(value).strip()
    if not s:
        return True, ""
    s_normalized = s.replace(",", ".")
    if _PESO_PATTERN.match(s) or _PESO_PATTERN.match(s_normalized):
        return True, ""
    return False, "El valor debe ser un número (coma o punto como decimal)."


def filter_empty_formula_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filtra filas donde materia_prima y porcentaje_peso estén ambos vacíos."""
    return [
        r
        for r in rows
        if (r.get("materia_prima") or "").strip() or (r.get("porcentaje_peso") or "").strip()
    ]


def formula_to_tsv(formula: List[Dict[str, Any]]) -> str:
    """Convierte la lista de fórmula a texto TSV (Materia prima TAB % peso) para copiar."""
    lines = []
    for row in formula:
        mp = (row.get("materia_prima") or "").strip()
        pct = (row.get("porcentaje_peso") or "").strip()
        lines.append(f"{mp}\t{pct}")
    return "\n".join(lines)
