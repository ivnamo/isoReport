"""
App ISO Report — Solo PASO 1 (cabecera / datos generales).

Entrada: listado jira iso + BBDD_Sesion-PT-INAVARRO.
Salida: JSON con bloque paso_1.
"""

from __future__ import annotations

import json

import streamlit as st

from iso_reports.data_loading import load_table
from iso_reports.paso1 import Paso1Error, build_all_paso1


def main() -> None:
    st.set_page_config(
        page_title="ISO Report · Paso 1",
        layout="wide",
    )
    st.title("Paso 1 — Cabecera / Datos generales")

    st.markdown(
        "Sube los dos archivos para generar el bloque **Paso 1**. "
        "No se procesan Paso 2, Paso 3 ni anexos; solo se devuelve el JSON de cabecera."
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

    if st.button("Generar Paso 1", type="primary"):
        try:
            resultado = build_all_paso1(df_jira, df_bbdd)
        except Paso1Error as e:
            st.error(str(e))
            return
        except Exception as exc:
            st.error(f"Error inesperado: {exc}")
            return

        n = len(resultado["paso_1"])
        st.success(f"Paso 1 generado correctamente: {n} solicitud(es).")
        st.subheader("Salida (JSON)")
        st.json(resultado)

        # También como texto para copiar
        json_str = json.dumps(resultado, ensure_ascii=False, indent=2)
        st.download_button(
            "Descargar JSON",
            data=json_str,
            file_name="paso_1.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
