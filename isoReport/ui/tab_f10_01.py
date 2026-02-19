"""
Tab F10-01: solo lectura. Muestra datos de la fila Excel en cards/secciones.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import streamlit as st

from models.solicitud import Solicitud

# Mapeo: etiqueta de visualización -> posibles nombres de columna en el Excel (el primero que exista en row se usa)
_F10_01_KEYS: Dict[str, tuple] = {
    "Nº Solicitud": ("Nº Solicitud", "Nº solicitud"),
    "Solicitante": ("Solicitante", "SOLICITANTE"),
    "Nombre proyecto": ("Nombre proyecto", "NOMBRE", "NOM_COMERCIAL"),
    "País destino": ("País destino", "PAÍS DESTINO", "PAIS DESTINO", "Pais destino"),
    "Aceptado": ("Aceptado", "ACEPTADO"),
    "Finalizado": ("Finalizado", "FINALIZADO"),
    "Necesidad": ("Necesidad", "NECESIDAD"),
    "Producto competencia": ("Producto competencia", "PRODUCTO COMPETENCIA"),
    "Volumen competencia": ("Volumen competencia", "VOLUMEN COMPETENCIA"),
    "Precio competencia": ("Precio competencia", "PRECIO COMPETENCIA"),
    "Volumen propuesto": ("Volumen propuesto", "VOLUMEN PROPUESTO"),
    "Envase": ("Envase", "ENVASE"),
    "Fecha aprobación solicitud": ("FECHA DE APROBACIÓN SOL.", "FECHA DE APROBACION SOL.", "Fecha aprobación solicitud", "FECHA APROBACIÓN SOLICITUD", "FECHA APROBACION SOLICITUD", "Fecha aprobación", "Fecha aprob. solicitud"),
    "Tiempo estimado (días laborables)": ("TIEMPO ESTIMADO (días laborables)", "TIEMPO ESTIMADO (DÍAS LABORABLES)", "Tiempo estimado (días laborables)", "Tiempo estimado", "Días laborables", "DIAS LABORABLES"),
    "Fecha finalización estimada": ("FECHA FINALIZACION ESTIMADA", "FECHA FINALIZACIÓN ESTIMADA", "Fecha finalización estimada", "Fecha fin. estimada"),
    "Fecha finalización real": ("FECHA DE FINALIZACION REAL", "FECHA FINALIZACIÓN REAL", "FECHA FINALIZACION REAL", "Fecha finalización real", "Fecha fin. real"),
    "Horas empleadas I+D": ("Horas empleadas I+D", "HORAS EMPLEADAS I+D"),
    "Horas empleadas Calidad": ("HORAS EMPLEADAS EN CALIDAD", "Horas empleadas Calidad", "HORAS EMPLEADAS CALIDAD"),
    "Motivo denegado": ("Motivo denegado", "MOTIVO DENEGADO"),
    "Problemas": ("Problemas", "PROBLEMAS"),
    "Comentarios": ("Comentarios", "COMENTARIOS"),
}


def _format_cell_value(v: Any) -> Any:
    """Formatea fechas y números serial de Excel para visualización."""
    if v is None or v == "":
        return ""
    s = str(v).strip().lower()
    if s == "nan" or s == "nat":
        return ""
    if hasattr(v, "strftime"):  # datetime / date / pandas Timestamp
        return v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else str(v)
    try:
        f = float(v)
        if f > 1e4 and f < 1e6:  # Excel serial (días desde 1900)
            d = datetime(1899, 12, 30) + timedelta(days=int(f))
            return d.strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        pass
    return v


def _row_val(row: Dict[str, Any], label: str) -> Any:
    """Devuelve el valor de la fila probando las posibles claves para esa etiqueta."""
    keys = _F10_01_KEYS.get(label, (label,))
    for k in keys:
        if k in row:
            v = row.get(k)
            if v is None:
                return ""
            return _format_cell_value(v)
    return ""


def render_tab_f10_01(solicitud: Solicitud) -> None:
    """Renderiza el tab F10-01 (viabilidad y planificación) en solo lectura desde solicitud.f10_01."""
    st.subheader("F10-01 — Viabilidad y planificación de diseños (solo lectura)")
    row = solicitud.f10_01 or {}
    if not row:
        st.info("Esta solicitud no tiene datos F10-01.")
        st.write("**Nº Solicitud:**", solicitud.display_numero)
        return

    with st.expander("Identificación", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if solicitud.id is not None:
                st.write("**ID:**", solicitud.id)
            st.write("**Nº Solicitud:**", solicitud.display_numero)
            st.write("**Solicitante:**", _row_val(row, "Solicitante"))
            st.write("**Nombre proyecto:**", _row_val(row, "Nombre proyecto"))
        with c2:
            st.write("**País destino:**", _row_val(row, "País destino"))
            st.write("**Aceptado:**", _row_val(row, "Aceptado"))
            st.write("**Finalizado:**", _row_val(row, "Finalizado"))

    with st.expander("Necesidad y contexto"):
        st.write("**Necesidad:**", _row_val(row, "Necesidad"))
        st.write("**Producto competencia:**", _row_val(row, "Producto competencia"))
        st.write("**Volumen competencia:**", _row_val(row, "Volumen competencia"))
        st.write("**Precio competencia:**", _row_val(row, "Precio competencia"))
        st.write("**Volumen propuesto:**", _row_val(row, "Volumen propuesto"))
        st.write("**Envase:**", _row_val(row, "Envase"))

    with st.expander("Planificación y fechas"):
        st.write("**Fecha aprobación solicitud:**", _row_val(row, "Fecha aprobación solicitud"))
        st.write("**Tiempo estimado (días laborables):**", _row_val(row, "Tiempo estimado (días laborables)"))
        st.write("**Fecha finalización estimada:**", _row_val(row, "Fecha finalización estimada"))
        st.write("**Fecha finalización real:**", _row_val(row, "Fecha finalización real"))
        st.write("**Horas empleadas I+D:**", _row_val(row, "Horas empleadas I+D"))
        st.write("**Horas empleadas Calidad:**", _row_val(row, "Horas empleadas Calidad"))

    with st.expander("Motivo denegado"):
        st.write(_row_val(row, "Motivo denegado") or "—")

    with st.expander("Problemas y comentarios"):
        st.write("**Problemas:**", _row_val(row, "Problemas") or "—")
        st.write("**Comentarios:**", _row_val(row, "Comentarios") or "—")
