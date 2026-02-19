"""
Filtros y listado de solicitudes en el sidebar.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

from models.solicitud import Solicitud


def _normalize_estado(val: any) -> str:
    """Normaliza Aceptado/Finalizado a mayúsculas para comparar Sí/No."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip().upper()


def _filter_solicitudes(
    solicitudes: List[Solicitud],
    year: int,
    estado_aceptado: Optional[str],
    estado_finalizado: Optional[str],
    pais: Optional[str],
    solicitante: Optional[str],
    nombre: Optional[str],
    search_text: Optional[str],
) -> List[Solicitud]:
    """Filtra la lista por año (ya aplicado), estado, país, solicitante, nombre y búsqueda libre."""
    out = solicitudes
    if estado_aceptado:
        filt = []
        for s in out:
            row = s.f10_01 or {}
            val = _normalize_estado(row.get("ACEPTADO") or row.get("Aceptado"))
            if estado_aceptado == "Sí" and (val == "SÍ" or val == "SI"):
                filt.append(s)
            elif estado_aceptado == "No" and (val == "NO" or val == ""):
                filt.append(s)
            elif estado_aceptado == "Todos":
                filt.append(s)
        if estado_aceptado != "Todos":
            out = filt
    if estado_finalizado:
        if estado_finalizado != "Todos":
            filt = []
            for s in out:
                row = s.f10_01 or {}
                val = _normalize_estado(row.get("FINALIZADO") or row.get("Finalizado"))
                if estado_finalizado == "Sí" and (val == "SÍ" or val == "SI"):
                    filt.append(s)
                elif estado_finalizado == "No" and (val == "NO" or val == ""):
                    filt.append(s)
            out = filt
    if pais:
        row_get = lambda s: (s.f10_01 or {}).get("PAIS DESTINO") or (s.f10_01 or {}).get("País destino")
        filt = [s for s in out if row_get(s) == pais]
        if filt or pais != "Todos":
            out = filt if filt else out
    if solicitante:
        if solicitante != "Todos":
            out = [s for s in out if ((s.f10_01 or {}).get("SOLICITANTE") or (s.f10_01 or {}).get("Solicitante")) == solicitante]
    if nombre:
        if nombre != "Todos":
            out = [s for s in out if ((s.f10_01 or {}).get("NOMBRE") or (s.f10_01 or {}).get("NOM_COMERCIAL") or (s.f10_01 or {}).get("Nombre proyecto")) == nombre]
    if search_text and search_text.strip():
        q = search_text.strip().lower()
        filt = []
        for s in out:
            row = s.f10_01 or {}
            f02 = s.f10_02 or {}
            text_parts = [
                str(s.numero_solicitud_canonico),
                str(row.get("SOLICITANTE") or row.get("Solicitante", "")),
                str(row.get("NOMBRE") or row.get("Nombre proyecto", "")),
                str(row.get("PAIS DESTINO") or row.get("País destino", "")),
                str(row.get("NOM_COMERCIAL", "")),
                str(f02.get("responsable", "")),
            ]
            if any(q in p.lower() for p in text_parts if p):
                filt.append(s)
        out = filt
    return out


def render_sidebar_filters_and_list(
    solicitudes: List[Solicitud],
    year: int,
) -> Optional[Solicitud]:
    """
    Renderiza en el sidebar los filtros y el listado de solicitudes.
    Devuelve la Solicitud seleccionada (de la lista filtrada) o None.
    """
    st.sidebar.header("Filtros")
    # Valores únicos para filtros (desde f10_01_row)
    aceptado_vals = ["Todos", "Sí", "No"]
    finalizado_vals = ["Todos", "Sí", "No"]
    def _get(row_key: str, alt: str = "") -> set:
        return set(
            (s.f10_01 or {}).get(row_key) or (s.f10_01 or {}).get(alt)
            for s in solicitudes
            if (s.f10_01 or {}).get(row_key) or (s.f10_01 or {}).get(alt)
        )
    paises = ["Todos"] + sorted(_get("PAIS DESTINO", "País destino"))
    solicitantes = ["Todos"] + sorted(_get("SOLICITANTE", "Solicitante"))
    nombres = ["Todos"] + sorted(_get("NOMBRE", "Nombre proyecto") | _get("NOM_COMERCIAL"))

    estado_aceptado = st.sidebar.selectbox("Aceptado", aceptado_vals, key="filtro_aceptado")
    estado_finalizado = st.sidebar.selectbox("Finalizado", finalizado_vals, key="filtro_finalizado")
    pais = st.sidebar.selectbox("País destino", paises, key="filtro_pais")
    solicitante = st.sidebar.selectbox("Solicitante", solicitantes, key="filtro_solicitante")
    nombre = st.sidebar.selectbox("Nombre proyecto", nombres, key="filtro_nombre")
    search_text = st.sidebar.text_input("Buscar (texto libre)", key="filtro_busqueda")

    filtered = _filter_solicitudes(
        solicitudes,
        year,
        estado_aceptado,
        estado_finalizado,
        pais,
        solicitante,
        nombre,
        search_text,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Solicitudes")

    if not filtered:
        st.sidebar.info("No hay solicitudes que coincidan con los filtros.")
        return None

    options = []
    for i, s in enumerate(filtered):
        label = s.display_numero
        if s.id is not None:
            label += f" (ID {s.id})"
        row = s.f10_01 or {}
        nom = row.get("NOMBRE") or row.get("NOM_COMERCIAL") or row.get("Nombre proyecto") or "—"
        label += f" — {str(nom)[:40]}"
        options.append(label)

    selected_idx = st.sidebar.selectbox(
        "Selecciona una solicitud",
        range(len(filtered)),
        format_func=lambda i: options[i],
        key="sidebar_select_solicitud",
    )
    return filtered[selected_idx]
