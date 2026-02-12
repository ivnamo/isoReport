from __future__ import annotations

from typing import List, Optional

import pandas as pd

from .bbdd_logic import ensure_bbdd_columns, group_bbdd_by_ensayo
from .jira_logic import attach_jira_to_ensayos
from .models import EspecificacionFinal, InformeData, ValidacionProducto


def build_informe_data(
    *,
    df_solicitudes: pd.DataFrame,
    df_bbdd: pd.DataFrame,
    df_jira: pd.DataFrame,
    numero_solicitud: str,
    jira_clave_liberada: Optional[str] = None,
) -> InformeData:
    """
    Construye un InformeData completo para un Nº de Solicitud concreto.

    - df_solicitudes: tabla de Solicitudes 2025 (una fila por proyecto).
    - df_bbdd: BBDD F10-02 con recetas.
    - df_jira: exportación de Jira.
    - numero_solicitud: Nº de Solicitud para el que se genera el informe.
    - jira_clave_liberada: Clave de incidencia Jira (ID-xx) elegida como LIBERADA.
    """
    # --- 1) Cabecera desde Solicitudes 2025 ---
    col_num = _find_best_column(df_solicitudes, ["Nº Solicitud", "Nº solicitud", "N_Solicitud"])
    if col_num is None:
        raise ValueError("No se ha encontrado una columna equivalente a 'Nº Solicitud' en Solicitudes 2025.")

    mask_sol = df_solicitudes[col_num].astype(str) == str(numero_solicitud)
    if not mask_sol.any():
        raise ValueError(f"No se ha encontrado la solicitud '{numero_solicitud}' en Solicitudes 2025.")

    sol_row = df_solicitudes[mask_sol].iloc[0]

    responsable = str(sol_row.get("Responsable", ""))
    tipo = str(sol_row.get("Tipo", ""))
    producto_base = str(sol_row.get("Producto base", ""))
    descripcion_diseno = str(sol_row.get("Descripción diseño", ""))
    producto_final = str(sol_row.get("Producto final", ""))
    formula_ok = str(sol_row.get("Fórmula OK", ""))
    riquezas = str(sol_row.get("Riquezas", ""))

    # --- 2) Ensayos desde BBDD ---
    df_bbdd = ensure_bbdd_columns(df_bbdd)
    df_bbdd_sel = df_bbdd[df_bbdd["Nº Solicitud"].astype(str) == str(numero_solicitud)]
    ensayos = group_bbdd_by_ensayo(df_bbdd_sel)

    # --- 3) Enriquecer ensayos con Jira ---
    if not df_jira.empty:
        ensayos = attach_jira_to_ensayos(ensayos, df_jira)

    # --- 4) Especificación final y validación desde Solicitudes ---
    espec = EspecificacionFinal(
        descripcion=str(sol_row.get("Spec_Descripcion", "")),
        aspecto=str(sol_row.get("Spec_Aspecto", "")),
        color=str(sol_row.get("Spec_Color", "")),
        densidad=str(sol_row.get("Spec_Densidad", "")),
        ph=str(sol_row.get("Spec_pH", "")),
        caracteristicas_quimicas=str(sol_row.get("Spec_Quimica", "")) or riquezas,
    )

    validacion = ValidacionProducto(
        fecha_validacion=str(sol_row.get("Fecha_Validacion", "")),
        comentario_validacion=str(sol_row.get("Validacion_JSON", "")),
    )

    informe = InformeData(
        responsable=responsable,
        numero_solicitud=str(numero_solicitud),
        tipo_solicitud=tipo,
        producto_base=producto_base,
        descripcion_diseno=descripcion_diseno,
        ensayos=ensayos,
        producto_final=producto_final,
        formula_ok=formula_ok,
        riquezas=riquezas,
        especificacion_final=espec,
        validacion_producto=validacion,
    )

    # --- 5) Ajustar verificación con Jira LIBERADA (si se ha elegido) ---
    if jira_clave_liberada and not df_jira.empty:
        mask_j = df_jira["Clave de incidencia"].astype(str) == str(jira_clave_liberada)
        if mask_j.any():
            row_j = df_jira[mask_j].iloc[0]
            # Si no había Fórmula OK, usamos el resumen de Jira.
            if not informe.formula_ok:
                informe.formula_ok = str(row_j.get("Resumen", ""))
            # Guardamos algunos extras en meta.
            informe.extra_meta["jira_liberada_clave"] = str(row_j.get("Clave de incidencia", ""))
            informe.extra_meta["jira_liberada_estado"] = str(row_j.get("Estado", ""))
            informe.extra_meta["jira_liberada_resumen"] = str(row_j.get("Resumen", ""))

    return informe


def _find_best_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Devuelve el primer nombre de columna existente entre los candidatos."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


