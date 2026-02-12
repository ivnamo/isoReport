"""
Capa de datos del editor de solicitudes ISO.

Transformación entre formato raw (paso_1[] + paso_2[]) y lista de solicitudes;
carga/guardado en disco; parseo de fórmula pegado; validación de % peso.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_JSON_PATH = "data/solicitudes.json"


def raw_to_solicitudes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convierte el JSON generado por la app (paso_1[] + paso_2[]) en lista de solicitudes.
    solicitudes[i] = { "paso_1": paso_1[i], "paso_2": paso_2[i] }.
    """
    paso_1_list = raw.get("paso_1") or []
    paso_2_list = raw.get("paso_2") or []
    n = min(len(paso_1_list), len(paso_2_list))
    return [
        {"paso_1": paso_1_list[i], "paso_2": paso_2_list[i]}
        for i in range(n)
    ]


def solicitudes_to_raw(solicitudes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convierte la lista de solicitudes de vuelta al formato raw (paso_1[] + paso_2[])
    para compatibilidad con el generador y guardado en disco.
    """
    paso_1 = [s["paso_1"] for s in solicitudes]
    paso_2 = [s["paso_2"] for s in solicitudes]
    return {"paso_1": paso_1, "paso_2": paso_2}


def load_solicitudes_json(path: str | Path) -> List[Dict[str, Any]]:
    """
    Carga el JSON desde disco y devuelve la lista de solicitudes.
    Si el fichero no existe o está vacío, devuelve [].
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return raw_to_solicitudes(raw)


def save_solicitudes_json(path: str | Path, solicitudes: List[Dict[str, Any]]) -> None:
    """
    Guarda la lista de solicitudes en disco en formato raw.
    Crea la carpeta padre si no existe.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = solicitudes_to_raw(solicitudes)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def parse_pasted_formula(text: str) -> List[Dict[str, str]]:
    """
    Parsea texto pegado (TAB o ; como separador) en filas de fórmula.
    - Trim por línea; ignora líneas vacías.
    - Cada línea: materia_prima, porcentaje_peso (si falta %, se deja vacío).
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


# Regex: número con coma o punto decimal (opcional)
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
    """
    Filtra filas donde materia_prima y porcentaje_peso estén ambos vacíos.
    """
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
