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

from iso_reports.paso1 import _normalize_id_for_match


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


# Columnas del CSV BBDD para verificación diseño (enriquecimiento)
VERIF_COL_ID_ENSAYO = "ID ensayo"
VERIF_COL_PRODUCTO_FINAL = "Producto final"
VERIF_COL_FORMULA_OK = "Fórmula OK"
VERIF_COL_RIQUEZAS = "Riquezas"


def get_id_ensayo_from_paso1_item(paso_1_item: Dict[str, Any]) -> str:
    """
    Obtiene el ID de ensayo desde un elemento de paso_1.
    Soporta formato plano (mapeo_id_ensayo_detectado) y anidado (mapeo.id_ensayo_detectado).
    """
    if not paso_1_item:
        return ""
    flat = paso_1_item.get("mapeo_id_ensayo_detectado")
    if flat is not None and str(flat).strip():
        return str(flat).strip()
    mapeo = paso_1_item.get("mapeo") or {}
    return str(mapeo.get("id_ensayo_detectado", "") or "").strip()


def _ensure_verificacion_diseno(paso_1_item: Dict[str, Any]) -> None:
    """Asegura que paso_1_item tenga verificacion_diseno con las tres claves."""
    if "verificacion_diseno" not in paso_1_item or not isinstance(paso_1_item["verificacion_diseno"], dict):
        paso_1_item["verificacion_diseno"] = {
            "producto_final": "",
            "formula_ok": "",
            "riquezas": "",
        }
    v = paso_1_item["verificacion_diseno"]
    for key in ("producto_final", "formula_ok", "riquezas"):
        if key not in v:
            v[key] = ""


def enriquecer_verificacion_diseno_desde_csv(
    solicitudes: List[Dict[str, Any]],
    df_bbdd: Any,
) -> List[Dict[str, Any]]:
    """
    Enriquece verificacion_diseno de cada paso_1 haciendo join por ID ensayo (normalizado).
    df_bbdd debe tener columnas "ID ensayo", y opcionalmente "Producto final", "Fórmula OK", "Riquezas".
    Si falta alguna columna, no falla y rellena solo las presentes.
    Modifica los elementos de solicitudes in-place y devuelve la misma lista.
    """
    import pandas as pd

    if not solicitudes or df_bbdd is None or (hasattr(df_bbdd, "empty") and df_bbdd.empty):
        return solicitudes

    col_id = VERIF_COL_ID_ENSAYO
    if col_id not in df_bbdd.columns:
        return solicitudes

    # Índice normalizado -> primera fila que tiene ese ID (para tomar una representante)
    id_to_row: Dict[str, pd.Series] = {}
    for idx, row in df_bbdd.iterrows():
        raw_id = row.get(col_id)
        nid = _normalize_id_for_match(str(raw_id) if raw_id is not None else "")
        if nid and nid not in id_to_row:
            id_to_row[nid] = row

    for sol in solicitudes:
        paso_1 = sol.get("paso_1") or {}
        id_ensayo = get_id_ensayo_from_paso1_item(paso_1)
        nid = _normalize_id_for_match(id_ensayo)
        if not nid or nid not in id_to_row:
            _ensure_verificacion_diseno(paso_1)
            continue
        row = id_to_row[nid]
        _ensure_verificacion_diseno(paso_1)
        v = paso_1["verificacion_diseno"]
        if VERIF_COL_PRODUCTO_FINAL in df_bbdd.columns:
            val = row.get(VERIF_COL_PRODUCTO_FINAL)
            v["producto_final"] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else ""
        if VERIF_COL_FORMULA_OK in df_bbdd.columns:
            val = row.get(VERIF_COL_FORMULA_OK)
            v["formula_ok"] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else ""
        if VERIF_COL_RIQUEZAS in df_bbdd.columns:
            val = row.get(VERIF_COL_RIQUEZAS)
            v["riquezas"] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else ""

    return solicitudes
