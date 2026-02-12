"""
App ISO Report — Paso 1 (cabecera) + Paso 2.1 (ensayos) + Paso 2.2 (fórmula/motivo) + Editor.

Modos: Generar JSON (desde Jira + BBDD) y Editar solicitudes (persistencia en disco).
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from iso_reports.data_loading import load_table
from iso_reports.editor_data import (
    DEFAULT_JSON_PATH,
    load_solicitudes_json,
    raw_to_solicitudes,
    save_solicitudes_json,
    solicitudes_to_raw,
)
from iso_reports.editor_ui import (
    render_detalle_solicitud,
    render_listado_solicitudes,
    render_panel_ensayo,
)
from iso_reports.paso1 import Paso1Error, build_all_paso1
from iso_reports.paso2 import Paso2Error, build_all_paso2_1, enrich_paso2_2


def _init_session_state() -> None:
    defaults = {
        "editor_mode": "generar",
        "solicitudes_data": None,
        "editor_solicitud_idx": None,
        "editor_ensayo_idx": None,
        "editor_json_path": DEFAULT_JSON_PATH,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _run_generar() -> None:
    st.title("Paso 1 + Paso 2.1 + Paso 2.2 — Cabecera, Ensayos y Fórmulas")
    st.markdown(
        "Sube los dos archivos para generar **Paso 1** (cabecera), **Paso 2.1** (ensayos por producto) y **Paso 2.2** (fórmula y motivo/comentario desde BBDD). "
        "No se generan Excel ni documentos finales."
    )
    col1, col2 = st.columns(2)
    with col1:
        jira_file = st.file_uploader(
            "1) Listado Jira ISO",
            type=["csv", "xlsx", "xls"],
            key="listado_jira",
            help="Tabla con columnas: Persona asignada, ProyectoID, Clave de incidencia",
        )
    with col2:
        bbdd_file = st.file_uploader(
            "2) BBDD_Sesion-PT-INAVARRO",
            type=["csv", "xlsx", "xls"],
            key="bbdd_sesion",
            help="Tabla con columna 'Descripción diseño' y referencia a ID ensayo",
        )

    if not jira_file or not bbdd_file:
        st.info("Sube ambos archivos para continuar.")
        return

    try:
        df_jira = load_table(jira_file)
        df_bbdd = load_table(bbdd_file)
    except Exception as exc:
        st.error(f"Error al cargar archivos: {exc}")
        return

    if st.button("Generar Paso 1 + Paso 2.1 + Paso 2.2", type="primary"):
        try:
            resultado = build_all_paso1(df_jira, df_bbdd)
            paso_1_lista = resultado["paso_1"]
            paso2_lista = build_all_paso2_1(df_jira, paso_1_lista)
            paso2_lista = enrich_paso2_2(paso2_lista, df_bbdd)
            resultado["paso_2"] = [
                {
                    "numero_solicitud": b["numero_solicitud"],
                    "producto_base_linea": b["producto_base_linea"],
                    "clave_incidencia_jira": b["clave_incidencia_jira"],
                    "ensayos": b["ensayos"],
                }
                for b in paso2_lista
            ]
        except Paso1Error as e:
            st.error(str(e))
            return
        except Paso2Error as e:
            st.error(str(e))
            return
        except Exception as exc:
            st.error(f"Error inesperado: {exc}")
            return

        n = len(resultado["paso_1"])
        st.success(f"Generado correctamente: {n} solicitud(es) con Paso 1, Paso 2.1 y Paso 2.2.")
        for i, b in enumerate(paso2_lista):
            if b.get("advertencia_sin_ensayos"):
                p = paso_1_lista[i]
                st.warning(
                    f"No hay filas en 'listado jira iso' con ProyectoID igual al producto de la solicitud "
                    f"nº {p.get('numero_solicitud', i+1)} (producto: «{p.get('producto_base_linea', '')}»)."
                )
        st.subheader("Salida (JSON)")
        st.json(resultado)
        json_str = json.dumps(resultado, ensure_ascii=False, indent=2)
        st.download_button(
            "Descargar JSON",
            data=json_str,
            file_name="paso_1_paso_2_1_paso_2_2.json",
            mime="application/json",
        )
        if st.button("Abrir en editor"):
            st.session_state["solicitudes_data"] = raw_to_solicitudes(resultado)
            st.session_state["editor_mode"] = "editar"
            st.session_state["editor_solicitud_idx"] = None
            st.session_state["editor_ensayo_idx"] = None
            st.rerun()


def _run_editar() -> None:
    st.title("Editar solicitudes ISO")
    path = Path(st.session_state.get("editor_json_path", DEFAULT_JSON_PATH))

    # Importar / Exportar
    with st.sidebar.expander("Importar / Exportar"):
        import_file = st.file_uploader("Importar JSON", type=["json"], key="editor_import")
        if import_file is not None:
            try:
                raw = json.load(import_file)
                st.session_state["solicitudes_data"] = raw_to_solicitudes(raw)
                st.success("JSON importado.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al importar: {e}")

    # Cargar datos: sesión o disco
    solicitudes = st.session_state.get("solicitudes_data")
    if solicitudes is None and path.exists():
        try:
            solicitudes = load_solicitudes_json(path)
            st.session_state["solicitudes_data"] = solicitudes
        except Exception as e:
            st.error(f"Error al cargar {path}: {e}")
            return

    if not solicitudes:
        st.info("No hay solicitudes cargadas. Importa un JSON (sidebar) o genera primero en el modo «Generar JSON».")
        return

    # Exportar JSON
    raw_export = solicitudes_to_raw(solicitudes)
    export_str = json.dumps(raw_export, ensure_ascii=False, indent=2)
    st.download_button(
        "Exportar JSON",
        data=export_str,
        file_name="solicitudes_iso.json",
        mime="application/json",
        key="editor_export",
    )

    search = st.text_input("Buscar (Nº solicitud, producto, responsable)", key="editor_search")
    sel_idx = render_listado_solicitudes(solicitudes, search or "")
    if sel_idx is None:
        return

    st.session_state["editor_solicitud_idx"] = sel_idx
    solicitud = solicitudes[sel_idx]
    ensayo_idx = render_detalle_solicitud(solicitud, sel_idx)
    if ensayo_idx is None:
        return

    st.session_state["editor_ensayo_idx"] = ensayo_idx
    ensayos = (solicitud.get("paso_2") or {}).get("ensayos") or []
    ensayo = ensayos[ensayo_idx]

    def on_save(ensayo_updated: dict) -> None:
        solicitudes[sel_idx]["paso_2"]["ensayos"][ensayo_idx] = ensayo_updated
        st.session_state["solicitudes_data"] = solicitudes
        try:
            save_solicitudes_json(path, solicitudes)
            st.success("Cambios guardados en disco.")
        except Exception as e:
            st.error(f"Error al guardar: {e}")
        st.rerun()

    def on_revert() -> None:
        if path.exists():
            try:
                loaded = load_solicitudes_json(path)
                st.session_state["solicitudes_data"] = loaded
                st.info("Cambios revertidos; recargado desde disco.")
            except Exception as e:
                st.error(f"Error al recargar: {e}")
        st.rerun()

    def on_apply_paste(formula_list: list) -> None:
        solicitudes[sel_idx]["paso_2"]["ensayos"][ensayo_idx]["formula"] = formula_list
        st.session_state["solicitudes_data"] = solicitudes

    render_panel_ensayo(
        ensayo,
        sel_idx,
        ensayo_idx,
        on_save=on_save,
        on_revert=on_revert,
        on_apply_paste=on_apply_paste,
    )


def main() -> None:
    st.set_page_config(page_title="ISO Report", layout="wide")
    _init_session_state()

    mode = st.sidebar.radio(
        "Modo",
        ("Generar JSON", "Editar solicitudes"),
        index=1 if st.session_state.get("editor_mode") == "editar" else 0,
        key="editor_mode_radio",
    )
    if mode == "Editar solicitudes":
        st.session_state["editor_mode"] = "editar"
    else:
        st.session_state["editor_mode"] = "generar"

    if st.session_state["editor_mode"] == "editar":
        _run_editar()
    else:
        _run_generar()


if __name__ == "__main__":
    main()
