"""
App ISO Report — Paso 1 (cabecera) + Paso 2.1 (ensayos/formulaciones).

Entrada: listado jira iso + BBDD_Sesion-PT-INAVARRO.
Salida: JSON con paso_1 y paso_2.ensayos.
"""

from __future__ import annotations

import json

import streamlit as st

from iso_reports.data_loading import load_table
from iso_reports.paso1 import Paso1Error, build_all_paso1
from iso_reports.paso2 import Paso2Error, build_all_paso2_1, enrich_paso2_2


def main() -> None:
    st.set_page_config(
        page_title="ISO Report · Paso 1",
        layout="wide",
    )
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
            # paso_2 con referencias explícitas a la solicitud y ensayos enriquecidos con fórmula/motivo
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
        # Advertencias si alguna solicitud no tiene ensayos
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


if __name__ == "__main__":
    main()
