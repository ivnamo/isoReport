"""
Tab Exportar: botones para generar y descargar F10-02 y F10-03 en XLSX.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from models.solicitud import Solicitud


def render_tab_exportar(
    solicitud: Solicitud,
    generate_f10_02_bytes: Callable[[Solicitud], bytes],
    generate_f10_03_bytes: Callable[[Solicitud], bytes],
) -> None:
    """Renderiza el tab Exportar con botones para generar XLSX."""
    st.subheader("Exportar documentos")

    if not solicitud.has_json_data():
        st.info("Inicializa esta solicitud en la bbdd para poder exportar.")
        return

    key_id = f"{solicitud.numero_solicitud_canonico}_{solicitud.year}"

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generar F10-02 (Diseño producto)", type="primary", key="export_f10_02"):
            try:
                data = generate_f10_02_bytes(solicitud)
                st.session_state["export_f10_02_bytes"] = data
                st.session_state["export_f10_02_for"] = key_id
                st.success("Generado. Usa el botón de descarga debajo.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al generar F10-02: {e}")
        if st.session_state.get("export_f10_02_for") == key_id and st.session_state.get("export_f10_02_bytes"):
            st.download_button(
                "Descargar F10-02.xlsx",
                data=st.session_state["export_f10_02_bytes"],
                file_name=f"F10-02_solicitud_{solicitud.numero_solicitud_canonico}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_f10_02",
            )
    with col2:
        if st.button("Generar F10-03 (Validación producto)", type="primary", key="export_f10_03"):
            try:
                data = generate_f10_03_bytes(solicitud)
                st.session_state["export_f10_03_bytes"] = data
                st.session_state["export_f10_03_for"] = key_id
                st.success("Generado. Usa el botón de descarga debajo.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al generar F10-03: {e}")
        if st.session_state.get("export_f10_03_for") == key_id and st.session_state.get("export_f10_03_bytes"):
            st.download_button(
                "Descargar F10-03.xlsx",
                data=st.session_state["export_f10_03_bytes"],
                file_name=f"F10-03_solicitud_{solicitud.numero_solicitud_canonico}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_f10_03",
            )
