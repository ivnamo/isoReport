"""
Tab F10-03: especificación final y validación. Edición + guardar.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import streamlit as st

from models.solicitud import Solicitud
from utils import ANEXO_F10_03_FILAS_VALIDACION, ensure_anexo_f10_03


def render_tab_f10_03(
    solicitud: Solicitud,
    on_save: Callable[[Dict[str, Any], Dict[str, Any]], None],
    on_mark_unsaved: Callable[[], None],
) -> None:
    """Renderiza el tab F10-03 (validación producto): especificación final y tabla validación."""
    st.subheader("F10-03 — Validación producto")

    if not solicitud.has_json_data():
        st.info("Inicializa esta solicitud en la bbdd para poder editar F10-03.")
        return

    p1 = dict(solicitud.paso_1)
    ensure_anexo_f10_03(p1)
    a = p1["anexo_f10_03"]
    esp = a["especificacion_final"]
    val = a["validacion"]
    filas: List[Dict[str, Any]] = list(val.get("filas") or [])

    # 1. Especificación final
    with st.expander("1. Especificación final", expanded=True):
        desc = st.text_area("Descripción", value=esp.get("descripcion") or "", height=120, key="f10_03_descripcion")
        aspecto = st.text_input("Aspecto", value=esp.get("aspecto") or "", key="f10_03_aspecto")
        color = st.text_input("Color", value=esp.get("color") or "", key="f10_03_color")
        car_quim = st.text_area(
            "Características químicas",
            value=esp.get("caracteristicas_quimicas") or "",
            height=150,
            key="f10_03_caracteristicas_quimicas",
        )
        a["especificacion_final"] = {
            "descripcion": desc,
            "aspecto": aspecto,
            "color": color,
            "caracteristicas_quimicas": car_quim,
        }
        if desc != esp.get("descripcion") or aspecto != esp.get("aspecto") or color != esp.get("color") or car_quim != esp.get("caracteristicas_quimicas"):
            on_mark_unsaved()

    # 2. Validación
    with st.expander("2. Validación", expanded=True):
        fecha_val = st.text_input("Fecha validación", value=val.get("fecha_validacion") or "", key="f10_03_fecha_validacion")
        val["fecha_validacion"] = fecha_val
        if fecha_val != (val.get("fecha_validacion") or ""):
            on_mark_unsaved()

        if not filas:
            filas = [dict(f) for f in ANEXO_F10_03_FILAS_VALIDACION]
        for i, f in enumerate(filas):
            with st.container():
                c1, c2, c3, c4 = st.columns([1, 2, 1, 2])
                with c1:
                    f["area"] = st.text_input("Área", value=f.get("area") or "", key=f"f10_03_fila_{i}_area")
                with c2:
                    f["aspecto_a_validar"] = st.text_input("Aspecto a validar", value=f.get("aspecto_a_validar") or "", key=f"f10_03_fila_{i}_aspecto")
                with c3:
                    f["validar_ok_nok"] = st.selectbox("OK/NOK", ["OK", "NOK"], index=0 if (f.get("validar_ok_nok") or "OK") == "OK" else 1, key=f"f10_03_fila_{i}_oknok")
                with c4:
                    f["comentarios"] = st.text_input("Comentarios", value=f.get("comentarios") or "", key=f"f10_03_fila_{i}_com")
        val["filas"] = filas

        if st.button("Añadir fila de validación", key="f10_03_add_fila"):
            filas.append({"area": "", "aspecto_a_validar": "", "validar_ok_nok": "OK", "comentarios": ""})
            on_mark_unsaved()
            st.rerun()

    st.markdown("---")
    if st.button("Guardar cambios", type="primary", key="f10_03_guardar"):
        on_save(p1, solicitud.paso_2)
