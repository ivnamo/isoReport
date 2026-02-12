"""
Paso 1: cabecera / datos generales.

Genera un Paso 1 por cada fila del listado Jira, enlazando con BBDD por
ID ensayo (BBDD) ↔ Clave de incidencia (Jira).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pandas as pd


# Alias por si el export tiene otro nombre para ProyectoID
JIRA_PROYECTO_ALIAS = ["ProyectoID", "Campo personalizado (ProyectoID)"]

BBDD_COLUMN_DESCRIPCION = "Descripción diseño"
BBDD_COLUMN_ID_ENSAYO = "ID ensayo"

# Detecta ID de ensayo en texto (ID-6, ID - 6, Ensayo 6, etc.)
ID_ENSAYO_REGEX = re.compile(
    r"ID\s*-\s*(\d+)|ID-(\d+)|Ensayo\s*(\d+)",
    re.IGNORECASE,
)


class Paso1Error(Exception):
    """Error de validación o construcción del Paso 1."""

    pass


def _normalize_id_for_match(value: str) -> str:
    """
    Normaliza un ID para comparación: devuelve forma canónica "ID-<número>".
    Así "ID-6", "ID - 6", "id-6", "Ensayo 6" coinciden todos.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    if not s:
        return ""
    m = ID_ENSAYO_REGEX.search(s)
    if m:
        num = m.group(1) or m.group(2) or m.group(3)
        return f"ID-{num}"
    # Sin patrón conocido: mayúsculas y espacios unificados
    return " ".join(s.upper().split())


def _find_column(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    """Devuelve la primera columna que exista en df con alguno de los nombres."""
    for name in names:
        if name in df.columns:
            return name
    return None


def _validate_jira_columns(df: pd.DataFrame) -> None:
    """Comprueba que el listado Jira tenga las columnas requeridas. Lanza Paso1Error si falta alguna."""
    missing = []
    # Persona asignada
    if "Persona asignada" not in df.columns:
        missing.append("Persona asignada")
    # ProyectoID (o alias)
    if _find_column(df, JIRA_PROYECTO_ALIAS) is None:
        missing.append("ProyectoID (o 'Campo personalizado (ProyectoID)')")
    # Clave de incidencia
    if "Clave de incidencia" not in df.columns:
        missing.append("Clave de incidencia")

    if missing:
        raise Paso1Error(
            f"En el archivo 'listado jira iso' faltan las siguientes columnas requeridas: {', '.join(missing)}."
        )


def _validate_bbdd_columns(df: pd.DataFrame) -> None:
    """Comprueba que la BBDD tenga al menos 'Descripción diseño'. Lanza Paso1Error si falta."""
    if BBDD_COLUMN_DESCRIPCION not in df.columns:
        raise Paso1Error(
            f"En el archivo 'BBDD_Sesion-PT-INAVARRO' falta la columna requerida: '{BBDD_COLUMN_DESCRIPCION}'."
        )


def _get_id_ensayo_from_bbdd_row(row: pd.Series, df: pd.DataFrame) -> str:
    """
    Obtiene el ID de ensayo de una fila de BBDD (valor en bruto para mostrar en mapeo).
    - Si existe columna 'ID ensayo', usa su valor.
    - Si no, busca en el texto de la fila con regex y devuelve el primer match tal cual.
    """
    if BBDD_COLUMN_ID_ENSAYO in df.columns:
        val = row.get(BBDD_COLUMN_ID_ENSAYO)
        if val is not None and str(val).strip() and str(val) != "nan":
            return str(val).strip()

    text_parts = []
    for _, v in row.items():
        if v is not None and isinstance(v, str) and v.strip():
            text_parts.append(v)
        elif v is not None and not isinstance(v, str):
            text_parts.append(str(v))
    full_text = " ".join(text_parts)
    match = ID_ENSAYO_REGEX.search(full_text)
    if match:
        return match.group(0).strip()
    return ""


def _find_bbdd_row_for_clave(df_bbdd: pd.DataFrame, clave_incidencia: str) -> Optional[pd.Series]:
    """
    Busca en la BBDD la primera fila cuyo ID de ensayo (columna o extraído) coincida
    con clave_incidencia. Comparación con normalización canónica (ID-<n>) para que
    "ID-6" y "ID - 6" coincidan.
    """
    clave_norm = _normalize_id_for_match(clave_incidencia)
    if not clave_norm:
        return None

    seen_canonical: set[str] = set()
    for _, row in df_bbdd.iterrows():
        row_id_raw = _get_id_ensayo_from_bbdd_row(row, df_bbdd)
        if not row_id_raw:
            continue
        row_id_norm = _normalize_id_for_match(row_id_raw)
        if row_id_norm in seen_canonical:
            continue
        seen_canonical.add(row_id_norm)
        if row_id_norm == clave_norm:
            return row
    return None


def build_paso1(
    df_jira: pd.DataFrame,
    df_bbdd: pd.DataFrame,
    *,
    numero_solicitud: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Construye UN solo Paso 1 (primera fila del listado Jira).
    Para generar todas las solicitudes use build_all_paso1.
    """
    all_result = build_all_paso1(df_jira, df_bbdd)
    items = all_result["paso_1"]
    if not items:
        raise Paso1Error("No se generó ninguna solicitud.")
    if numero_solicitud is not None:
        for item in items:
            if item.get("numero_solicitud") == numero_solicitud:
                return {"paso_1": item}
    return {"paso_1": items[0]}


def build_all_paso1(
    df_jira: pd.DataFrame,
    df_bbdd: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Construye un Paso 1 por cada fila del listado Jira (todas las solicitudes).
    - responsable, producto_base_linea, clave_incidencia: de cada fila Jira.
    - descripcion_partida_diseno: de la fila de BBDD cuyo ID ensayo coincide con Clave de incidencia (Jira).
    - numero_solicitud: 1, 2, 3, ... (incremental).
    - mapeo: id_ensayo_detectado (valor en BBDD) y clave_incidencia_jira (valor en Jira) del enlace.
    """
    _validate_jira_columns(df_jira)
    _validate_bbdd_columns(df_bbdd)

    if df_jira.empty:
        raise Paso1Error("El archivo 'listado jira iso' está vacío (sin filas).")
    if df_bbdd.empty:
        raise Paso1Error("El archivo 'BBDD_Sesion-PT-INAVARRO' está vacío (sin filas).")

    col_proyecto = _find_column(df_jira, JIRA_PROYECTO_ALIAS)
    lista: List[Dict[str, Any]] = []

    for num, (_, jira_row) in enumerate(df_jira.iterrows(), start=1):
        numero_solicitud = num
        responsable = str(jira_row.get("Persona asignada", "")).strip()
        producto_base_linea = (
            str(jira_row.get(col_proyecto, "")).strip() if col_proyecto else ""
        )
        clave_incidencia_jira = str(jira_row.get("Clave de incidencia", "")).strip()

        descripcion_partida_diseno = ""
        id_ensayo_detectado = ""

        bbdd_row = _find_bbdd_row_for_clave(df_bbdd, clave_incidencia_jira)
        if bbdd_row is not None:
            descripcion_partida_diseno = str(
                bbdd_row.get(BBDD_COLUMN_DESCRIPCION, "")
            ).strip()
            id_ensayo_detectado = _get_id_ensayo_from_bbdd_row(bbdd_row, df_bbdd)
        if not id_ensayo_detectado and clave_incidencia_jira:
            id_ensayo_detectado = clave_incidencia_jira

        lista.append({
            "responsable": responsable,
            "numero_solicitud": numero_solicitud,
            "tipo": "Interna",
            "producto_base_linea": producto_base_linea,
            "descripcion_partida_diseno": descripcion_partida_diseno,
            "mapeo": {
                "id_ensayo_detectado": id_ensayo_detectado,
                "clave_incidencia_jira": clave_incidencia_jira,
            },
        })

    return {"paso_1": lista}
