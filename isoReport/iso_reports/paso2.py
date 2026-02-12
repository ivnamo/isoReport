"""
Paso 2: Ensayos / Formulaciones.

- Paso 2.1: listado de ensayos (id, ensayo, fecha, resultado) filtrado por producto.
- Paso 2.2: enriquecimiento con fórmula (materia prima + % peso) y motivo/comentario desde BBDD.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .paso1 import JIRA_PROYECTO_ALIAS, _find_column, _normalize_id_for_match


# Columnas obligatorias en listado Jira para Paso 2.1
PASO2_1_JIRA_COLUMNS = [
    "Clave de incidencia",
    "Resumen",
    "Creada",
    "Estado",
]

# Columnas obligatorias en BBDD para Paso 2.2 (fórmula y motivo/comentario)
BBDD_COLUMNS_PASO2_2 = [
    "ID ensayo",
    "Materia prima",
    "% peso",
    "Motivo / comentario",
]


class Paso2Error(Exception):
    """Error de validación o construcción del Paso 2."""

    pass


def _validate_jira_columns_paso2_1(df: pd.DataFrame) -> str:
    """
    Comprueba que el listado Jira tenga las columnas requeridas para Paso 2.1.
    Devuelve el nombre de la columna de ProyectoID usada.
    Lanza Paso2Error si falta alguna.
    """
    missing = []
    for col in PASO2_1_JIRA_COLUMNS:
        if col not in df.columns:
            missing.append(col)
    col_proyecto = _find_column(df, JIRA_PROYECTO_ALIAS)
    if col_proyecto is None:
        missing.append("ProyectoID (o 'Campo personalizado (ProyectoID)')")

    if missing:
        raise Paso2Error(
            f"En el archivo 'listado jira iso' faltan las siguientes columnas requeridas para Paso 2.1: {', '.join(missing)}."
        )
    return col_proyecto


def build_paso2_1(
    df_jira: pd.DataFrame,
    producto_base_linea: str,
) -> Dict[str, Any]:
    """
    Construye el bloque Paso 2.1 (ensayos/formulaciones) para un producto dado.

    Filtra las filas de listado Jira donde ProyectoID == producto_base_linea
    y mapea: id (Clave de incidencia), ensayo (Resumen), fecha (Creada), resultado (Estado).

    No incluye fórmula ni motivo/comentario (Paso 2.2 y 2.3).

    Devuelve {"ensayos": [...], "advertencia_sin_ensayos": bool}.
    Si no hay filas que cumplan el filtro, ensayos es [] y advertencia_sin_ensayos True.
    """
    col_proyecto = _validate_jira_columns_paso2_1(df_jira)

    producto = str(producto_base_linea).strip()
    df_jira = df_jira.copy()
    col_vals = df_jira[col_proyecto].astype(str).str.strip()
    mask = col_vals == producto
    df_filtrado = df_jira[mask]

    ensayos: List[Dict[str, Any]] = []
    for _, row in df_filtrado.iterrows():
        ensayos.append({
            "id": str(row.get("Clave de incidencia", "")).strip(),
            "ensayo": str(row.get("Resumen", "")).strip(),
            "fecha": str(row.get("Creada", "")).strip(),
            "resultado": str(row.get("Estado", "")).strip(),
        })

    advertencia_sin_ensayos = len(ensayos) == 0
    return {
        "ensayos": ensayos,
        "advertencia_sin_ensayos": advertencia_sin_ensayos,
    }


def build_all_paso2_1(
    df_jira: pd.DataFrame,
    paso_1_lista: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Construye Paso 2.1 para cada elemento de paso_1 (por producto_base_linea).

    Cada bloque incluye referencias a la solicitud para poder relacionar sin depender del índice:
    numero_solicitud, producto_base_linea, clave_incidencia_jira (del mapeo de paso_1).
    Devuelve lista de dicts con: ensayos, advertencia_sin_ensayos, numero_solicitud,
    producto_base_linea, clave_incidencia_jira.
    """
    if not paso_1_lista:
        return []

    _validate_jira_columns_paso2_1(df_jira)

    resultado: List[Dict[str, Any]] = []
    for p in paso_1_lista:
        producto = p.get("producto_base_linea", "")
        bloque = build_paso2_1(df_jira, producto)
        bloque["numero_solicitud"] = p.get("numero_solicitud")
        bloque["producto_base_linea"] = producto
        bloque["clave_incidencia_jira"] = (
            (p.get("mapeo") or {}).get("clave_incidencia_jira", "")
        )
        resultado.append(bloque)
    return resultado


def _validate_bbdd_columns_paso2_2(df_bbdd: pd.DataFrame) -> None:
    """Comprueba que la BBDD tenga las columnas requeridas para Paso 2.2. Lanza Paso2Error si falta alguna."""
    missing = [c for c in BBDD_COLUMNS_PASO2_2 if c not in df_bbdd.columns]
    if missing:
        raise Paso2Error(
            f"En el archivo 'BBDD_Sesion-PT-INAVARRO' faltan las siguientes columnas requeridas para Paso 2.2: {', '.join(missing)}."
        )


def _get_bbdd_rows_for_ensayo_id(df_bbdd: pd.DataFrame, ensayo_id: str) -> pd.DataFrame:
    """Devuelve todas las filas de BBDD donde ID ensayo (normalizado) coincide con ensayo_id (normalizado)."""
    ensayo_norm = _normalize_id_for_match(ensayo_id)
    if not ensayo_norm:
        return df_bbdd.iloc[0:0]
    col_id = "ID ensayo"
    if col_id not in df_bbdd.columns:
        return df_bbdd.iloc[0:0]
    mask = df_bbdd[col_id].apply(lambda v: _normalize_id_for_match(str(v) if v is not None else "") == ensayo_norm)
    return df_bbdd[mask].copy()


def enrich_paso2_2(
    paso2_lista: List[Dict[str, Any]],
    df_bbdd: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Enriquece cada ensayo en paso2_lista con fórmula (materia prima + % peso) y motivo_comentario desde BBDD.

    JOIN: BBDD.ID ensayo (normalizado) == ensayo.id (normalizado).
    - formula: lista de { materia_prima, porcentaje_peso } por cada fila BBDD coincidente.
    - motivo_comentario: primer valor no vacío de "Motivo / comentario" entre las filas coincidentes; si vacío no se añade la clave.
    Si no hay filas coincidentes en BBDD, no se añaden formula ni motivo_comentario al ensayo.
    """
    _validate_bbdd_columns_paso2_2(df_bbdd)

    result: List[Dict[str, Any]] = []
    for bloque in paso2_lista:
        new_bloque = {**bloque, "ensayos": []}
        for ensayo in bloque.get("ensayos", []):
            enr = dict(ensayo)
            ensayo_id = (enr.get("id") or "").strip()
            df_match = _get_bbdd_rows_for_ensayo_id(df_bbdd, ensayo_id)
            if not df_match.empty:
                formula: List[Dict[str, Any]] = []
                for _, row in df_match.iterrows():
                    mp = row.get("Materia prima")
                    pct_val = row.get("% peso")
                    materia = "" if mp is None or (isinstance(mp, float) and pd.isna(mp)) else str(mp).strip()
                    pct = "" if pct_val is None or (isinstance(pct_val, float) and pd.isna(pct_val)) else str(pct_val).strip()
                    formula.append({
                        "materia_prima": materia,
                        "porcentaje_peso": pct,
                    })
                enr["formula"] = formula
                motivo = ""
                for _, row in df_match.iterrows():
                    v = row.get("Motivo / comentario")
                    if v is not None and str(v).strip() and str(v) != "nan":
                        motivo = str(v).strip()
                        break
                if motivo:
                    enr["motivo_comentario"] = motivo
            new_bloque["ensayos"].append(enr)
        result.append(new_bloque)
    return result
