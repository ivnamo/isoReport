from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .models import Ensayo


def attach_jira_to_ensayos(
    ensayos: List[Ensayo],
    df_jira: pd.DataFrame,
    *,
    col_clave: str = "Clave de incidencia",
    normalize_ids: bool = True,
) -> List[Ensayo]:
    """
    Enlaza cada Ensayo con su fila correspondiente en Jira, usando
    ID ensayo ↔ columna `col_clave`.

    - `normalize_ids=True` hace una normalización simple: strip() y mayúsculas.
    """
    if col_clave not in df_jira.columns:
        # No podemos asociar nada, devolvemos ensayos tal cual.
        return ensayos

    def _norm(v: str) -> str:
        return str(v).strip().upper()

    jira_index: Dict[str, pd.Series] = {}
    for _, row in df_jira.iterrows():
        key = _norm(row[col_clave]) if normalize_ids else str(row[col_clave])
        # Si hay duplicados se sobrescriben; el caso multi-issue se gestionará
        # a nivel de selección de LIBERADO, no aquí.
        jira_index[key] = row

    for ensayo in ensayos:
        key = _norm(ensayo.id_ensayo) if normalize_ids else ensayo.id_ensayo
        row = jira_index.get(key)
        if row is None:
            continue

        ensayo.jira_tipo_incidencia = str(row.get("Tipo de Incidencia", ""))
        ensayo.jira_clave = str(row.get("Clave de incidencia", ""))
        ensayo.jira_id = str(row.get("ID de la incidencia", ""))
        ensayo.jira_resumen = str(row.get("Resumen", ""))
        ensayo.jira_proyecto_id = str(row.get("Campo personalizado (ProyectoID)", ""))
        ensayo.jira_persona_asignada = str(row.get("Persona asignada", ""))
        ensayo.jira_estado = str(row.get("Estado", ""))
        ensayo.jira_fecha_creada = str(row.get("Creada", ""))
        ensayo.jira_fecha_vencimiento = str(row.get("Fecha de vencimiento", ""))
        ensayo.jira_fecha_actualizada = str(row.get("Actualizada", ""))
        ensayo.jira_fecha_resuelta = str(row.get("Resuelta", ""))
        ensayo.jira_descripcion = str(row.get("Descripción", ""))

        # Algunas exportaciones de Jira pueden tener varias columnas de Comentarios / Etiquetas.
        comentarios_cols = [c for c in df_jira.columns if c.startswith("Comentarios")]
        comentarios_values: List[str] = []
        for c in comentarios_cols:
            v = str(row.get(c, "")).strip()
            if v and v != "nan":
                comentarios_values.append(v)
        ensayo.jira_comentarios_resumen = "\n\n".join(comentarios_values)

        etiquetas_cols = [c for c in df_jira.columns if c.startswith("Etiquetas")]
        etiquetas_values: List[str] = []
        for c in etiquetas_cols:
            v = str(row.get(c, "")).strip()
            if v and v != "nan":
                etiquetas_values.append(v)
        ensayo.jira_etiquetas = ", ".join(sorted(set(etiquetas_values)))

        ensayo.jira_prioridad = str(row.get("Prioridad", ""))

    return ensayos


def find_liberado_candidates(
    df_jira: pd.DataFrame,
    *,
    col_estado: str = "Estado",
    col_clave: str = "Clave de incidencia",
) -> pd.DataFrame:
    """
    Devuelve un subconjunto de df_jira con las issues en estado LIBERADO
    (case-insensitive). Se puede filtrar luego por Nº de Solicitud o ProyectoID
    desde la UI, si es necesario.
    """
    if col_estado not in df_jira.columns:
        return df_jira.iloc[0:0]  # vacío con mismas columnas

    mask = df_jira[col_estado].astype(str).str.upper() == "LIBERADO"
    return df_jira[mask].copy()


