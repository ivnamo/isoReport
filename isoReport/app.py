"""
App F10: gestión de F10-01 (lectura Excel), F10-02 y F10-03 (edición JSON, exportación).
"""

from __future__ import annotations

import copy
from pathlib import Path

import streamlit as st

import config
from exporters import build_f10_02_bytes, build_f10_03_bytes
from models.solicitud import Solicitud
from services import (
    build_unified_list,
    load_f10_01_sheet,
    load_raw,
    save_raw,
    unified_list_to_raw,
)
from services.f10_01_loader import get_available_years
from ui import (
    render_sidebar_filters_and_list,
    render_tab_exportar,
    render_tab_f10_01,
    render_tab_f10_02,
    render_tab_f10_03,
)
from utils.solicitud_data import ensure_anexo_f10_03


def _init_session_state() -> None:
    defaults = {
        "unified_list": None,
        "year": 2025,
        "selected_filtered_idx": None,
        "editing_solicitud": None,
        "unsaved_changes": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _ensure_verificacion(p1: dict) -> None:
    if "verificacion_diseno" not in p1 or not isinstance(p1["verificacion_diseno"], dict):
        p1["verificacion_diseno"] = {"producto_final": "", "formula_ok": "", "riquezas": ""}
    for k in ("producto_final", "formula_ok", "riquezas"):
        if k not in p1["verificacion_diseno"]:
            p1["verificacion_diseno"][k] = ""


def main() -> None:
    st.set_page_config(page_title="F10 Gestión", layout="wide")
    _init_session_state()

    json_path = config.DEFAULT_JSON_PATH
    f10_01_path = config.DEFAULT_F10_01_PATH

    if not f10_01_path.exists():
        st.warning(f"No se encuentra el Excel F10-01 en {f10_01_path}. Usa solo datos de la bbdd.")
    if not json_path.exists():
        st.warning(f"No se encuentra el JSON en {json_path}. Carga un JSON o crea solicitudes desde F10-01.")

    years = get_available_years(f10_01_path)
    year = st.sidebar.selectbox("Año", options=years, index=0, key="app_year")
    st.session_state["year"] = year

    df_f10_01 = load_f10_01_sheet(str(f10_01_path), year)
    try:
        raw = load_raw(json_path)
    except Exception as e:
        st.error(f"Error al cargar JSON: {e}")
        raw = {"paso_1": [], "paso_2": []}

    unified_list = build_unified_list(df_f10_01, raw, year)
    st.session_state["unified_list"] = unified_list

    current: Solicitud | None = render_sidebar_filters_and_list(unified_list, year)

    if current is None:
        st.info("Selecciona una solicitud en la barra lateral.")
        return

    idx_in_unified = next(
        (i for i, s in enumerate(unified_list) if
         s.numero_solicitud_canonico == current.numero_solicitud_canonico
         and s.year == current.year
         and (s.paso_1.get("producto_base_linea") or "") == (current.paso_1.get("producto_base_linea") or "")),
        None,
    )
    if idx_in_unified is None:
        idx_in_unified = 0
        current = unified_list[0]

    if st.session_state.get("editing_solicitud") is None or st.session_state.get("editing_solicitud_key") != (current.numero_solicitud_canonico, current.year):
        st.session_state["editing_solicitud"] = copy.deepcopy(current)
        st.session_state["editing_solicitud_key"] = (current.numero_solicitud_canonico, current.year)
        st.session_state["unsaved_changes"] = False

    editing: Solicitud = st.session_state["editing_solicitud"]

    if st.session_state.get("unsaved_changes"):
        st.warning("Tienes cambios sin guardar.")

    st.title(f"Solicitud {editing.numero_solicitud_canonico} — {(editing.f10_01_row or {}).get('Nombre proyecto') or editing.paso_1.get('producto_base_linea') or '—'}")

    if editing.origen == "solo_f10_01" and not editing.has_json_data():
        if st.button("Inicializar en bbdd", type="primary", key="init_bbdd"):
            p1 = dict(editing.paso_1)
            p2 = dict(editing.paso_2)
            _ensure_verificacion(p1)
            editing.paso_1 = p1
            editing.paso_2 = p2
            unified_list[idx_in_unified] = editing
            raw_new = unified_list_to_raw(unified_list)
            try:
                save_raw(json_path, raw_new)
                st.success("Solicitud inicializada en la bbdd.")
                st.session_state["unsaved_changes"] = False
                st.session_state["editing_solicitud"] = copy.deepcopy(editing)
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    tab1, tab2, tab3, tab4 = st.tabs(["F10-01", "F10-02", "F10-03", "Exportar"])

    with tab1:
        render_tab_f10_01(editing)

    def _on_save_f10_02(p1: dict, p2: dict) -> None:
        _ensure_verificacion(p1)
        editing.paso_1 = p1
        editing.paso_2 = p2
        unified_list[idx_in_unified] = editing
        raw_new = unified_list_to_raw(unified_list)
        try:
            save_raw(json_path, raw_new)
            st.session_state["unsaved_changes"] = False
            st.session_state["editing_solicitud"] = copy.deepcopy(editing)
            st.success("Cambios guardados.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    def _on_save_f10_03(p1: dict, p2: dict) -> None:
        ensure_anexo_f10_03(p1)
        editing.paso_1 = p1
        editing.paso_2 = p2
        unified_list[idx_in_unified] = editing
        raw_new = unified_list_to_raw(unified_list)
        try:
            save_raw(json_path, raw_new)
            st.session_state["unsaved_changes"] = False
            st.session_state["editing_solicitud"] = copy.deepcopy(editing)
            st.success("Cambios guardados.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

    def _mark_unsaved() -> None:
        st.session_state["unsaved_changes"] = True

    with tab2:
        render_tab_f10_02(editing, _on_save_f10_02, _mark_unsaved)

    with tab3:
        render_tab_f10_03(editing, _on_save_f10_03, _mark_unsaved)

    with tab4:
        render_tab_exportar(editing, build_f10_02_bytes, build_f10_03_bytes)


if __name__ == "__main__":
    main()
