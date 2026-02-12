from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from iso_reports import bbdd_logic, data_loading, jira_logic, report_builder
from iso_reports.models import InformeData
from iso_reports.template_iso_csv import build_informe_iso_csv
from iso_reports.template_iso_xlsx import create_iso_workbook, workbook_to_bytes


def _init_session_state() -> None:
    defaults = {
        "solicitudes_df": None,
        "bbdd_df": pd.DataFrame(columns=bbdd_logic.BBDD_COLUMNS_BASE),
        "jira_df": None,
        "registro_num_solicitud": None,
        "informe_num_solicitud": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def main() -> None:
    st.set_page_config(
        page_title="F10-02 / F10-03 · Informes ISO",
        layout="wide",
    )
    _init_session_state()

    st.title("F10-02 / F10-03 · Diseño, Ensayos y Generación de Informes ISO")

    mode = st.sidebar.radio(
        "Modo",
        (
            "Registrar diseños y ensayos (F10-02/F10-03)",
            "Generar informes ISO (Solicitudes + BBDD + Jira)",
        ),
    )

    if mode.startswith("Registrar"):
        pantalla_registro()
    else:
        pantalla_informes()


# ---------------------------------------------------------------------------
# Pantalla 1: Registro de diseños y ensayos
# ---------------------------------------------------------------------------


def pantalla_registro() -> None:
    st.subheader("📥 Carga de datos base")

    col1, col2 = st.columns(2)
    with col1:
        solicitudes_file = st.file_uploader(
            "Solicitudes 2025 (Excel)",
            type=["xlsx", "xls"],
            key="solicitudes_registro",
        )
        if solicitudes_file is not None:
            try:
                df_sol = data_loading.load_solicitudes_excel(solicitudes_file)
                st.session_state["solicitudes_df"] = df_sol
                st.success(f"Cargadas {len(df_sol)} filas de Solicitudes 2025.")
            except Exception as exc:  # pragma: no cover - errores runtime
                st.error(f"Error cargando Solicitudes 2025: {exc}")

    with col2:
        bbdd_file = st.file_uploader(
            "BBDD F10-02 existente (CSV, opcional)",
            type=["csv"],
            key="bbdd_registro",
        )
        if bbdd_file is not None:
            try:
                df_bbdd = data_loading.load_bbdd_csv(bbdd_file)
                df_bbdd = bbdd_logic.ensure_bbdd_columns(df_bbdd)
                st.session_state["bbdd_df"] = df_bbdd
                st.success(f"Cargadas {len(df_bbdd)} filas en la BBDD F10-02.")
            except Exception as exc:
                st.error(f"Error cargando BBDD F10-02: {exc}")

    solicitudes_df: Optional[pd.DataFrame] = st.session_state.get("solicitudes_df")

    st.markdown("---")
    st.subheader("1. Datos de partida del diseño (cabecera por Nº Solicitud)")

    if solicitudes_df is None or solicitudes_df.empty:
        st.info(
            "Sube primero el Excel de **Solicitudes 2025** para poder seleccionar "
            "un Nº de Solicitud y precargar la cabecera."
        )
        return

    col_num = "Nº Solicitud" if "Nº Solicitud" in solicitudes_df.columns else solicitudes_df.columns[0]
    solicitudes_unicas = (
        solicitudes_df[col_num].astype(str).dropna().unique().tolist()
    )
    solicitudes_unicas = sorted(solicitudes_unicas, key=lambda x: str(x))

    default_value = st.session_state.get("registro_num_solicitud") or (
        solicitudes_unicas[0] if solicitudes_unicas else ""
    )

    num_solicitud = st.selectbox(
        "Nº Solicitud",
        options=solicitudes_unicas,
        index=solicitudes_unicas.index(default_value)
        if default_value in solicitudes_unicas
        else 0,
    )
    st.session_state["registro_num_solicitud"] = num_solicitud

    mask_sol = solicitudes_df[col_num].astype(str) == str(num_solicitud)
    sol_row = solicitudes_df[mask_sol].iloc[0]

    colA, colB = st.columns(2)
    with colA:
        responsable = st.text_input(
            "Responsable de proyecto",
            value=str(sol_row.get("Responsable", "")),
        )
        tipo = st.text_input(
            "Tipo de solicitud",
            value=str(sol_row.get("Tipo", "")),
        )
        producto_base = st.text_input(
            "Producto base / línea",
            value=str(sol_row.get("Producto base", "")),
        )
    with colB:
        descripcion_diseno = st.text_area(
            "Descripción de los datos de partida del diseño",
            value=str(sol_row.get("Descripción diseño", "")),
            height=120,
        )

    st.markdown("### 2. Ensayo / formulación")
    colE1, colE2, colE3, colE4 = st.columns(4)
    with colE1:
        id_ensayo = st.text_input("ID ensayo (ej. ID-44)", value="")
    with colE2:
        nombre_ensayo = st.text_input(
            "Nombre formulación",
            value=str(sol_row.get("Nombre formulación", "")),
        )
    with colE3:
        fecha_ensayo = st.date_input("Fecha ensayo", value=date.today())
    with colE4:
        resultado_ensayo = st.selectbox(
            "Resultado", ["NOK", "OK", "OK NO LIBERADO"], index=1
        )

    motivo_modificacion = st.text_area(
        "Motivo / comentario (NOK, observaciones)",
        value=str(sol_row.get("Motivo / comentario", "")),
        height=120,
    )

    st.markdown("#### Receta del ensayo (pegar desde Excel)")
    receta_text = st.text_area(
        "Cada línea: materia prima + % peso (tabulado, punto y coma o espacio)",
        value="",
        height=140,
        key="receta_textarea_registro",
    )

    st.markdown("### 3. Verificación (campos propuestos desde Solicitudes)")
    colV1, colV2, colV3 = st.columns(3)
    with colV1:
        producto_verificacion = st.text_input(
            "Producto final",
            value=str(sol_row.get("Producto final", "")),
        )
    with colV2:
        formula_ok = st.text_input(
            "Fórmula OK (ref. ensayo / versión)",
            value=str(sol_row.get("Fórmula OK", "")),
        )
    with colV3:
        riquezas = st.text_input(
            "Riquezas (garantías, NPK, micro...)",
            value=str(sol_row.get("Riquezas", "")),
        )

    if st.button(
        "➕ Añadir ensayo al registro F10-02",
        type="primary",
        use_container_width=True,
    ):
        if not receta_text.strip():
            st.error("Primero pega la receta del ensayo.")
        elif not id_ensayo.strip():
            st.error("Rellena el ID de ensayo.")
        else:
            materias = bbdd_logic.parse_receta_text(receta_text)
            if not materias:
                st.error(
                    "No se han encontrado líneas válidas (materia prima + %). "
                    "Revisa el texto pegado."
                )
            else:
                df_new = bbdd_logic.build_new_bbdd_rows_from_receta(
                    responsable=responsable,
                    numero_solicitud=str(num_solicitud),
                    tipo=tipo,
                    producto_base=producto_base,
                    descripcion_diseno=descripcion_diseno,
                    id_ensayo=id_ensayo,
                    nombre_formulacion=nombre_ensayo,
                    fecha_ensayo=fecha_ensayo.strftime("%Y-%m-%d"),
                    resultado=resultado_ensayo,
                    motivo=motivo_modificacion,
                    producto_final=producto_verificacion,
                    formula_ok=formula_ok,
                    riquezas=riquezas,
                    materias=materias,
                )
                st.session_state["bbdd_df"] = pd.concat(
                    [st.session_state["bbdd_df"], df_new],
                    ignore_index=True,
                )
                st.success(
                    f"Añadidas {len(df_new)} líneas para el ensayo {id_ensayo.strip()}."
                )

    st.markdown("### Tabla BBDD F10-02 (toda la sesión)")
    st.dataframe(
        st.session_state["bbdd_df"],
        use_container_width=True,
        height=320,
    )

    colB1, colB2 = st.columns(2)
    with colB1:
        if st.button(
            "🗑️ Borrar TODA la BBDD de esta sesión",
            use_container_width=True,
        ):
            st.session_state["bbdd_df"] = pd.DataFrame(
                columns=bbdd_logic.BBDD_COLUMNS_BASE
            )
            st.warning("BBDD vaciada en esta sesión.")
    with colB2:
        if not st.session_state["bbdd_df"].empty:
            _download_df_as_csv(
                st.session_state["bbdd_df"],
                filename="F10_02_BD_ensayos.csv",
                label="📥 Descargar BBDD F10-02 (CSV)",
            )


# ---------------------------------------------------------------------------
# Pantalla 2: Generación de informes ISO
# ---------------------------------------------------------------------------


def pantalla_informes() -> None:
    st.subheader("📥 Cargar archivos de origen")

    col1, col2, col3 = st.columns(3)

    with col1:
        solicitudes_file = st.file_uploader(
            "Solicitudes 2025 (Excel)",
            type=["xlsx", "xls"],
            key="solicitudes_informes",
        )
        if solicitudes_file is not None:
            try:
                df_sol = data_loading.load_solicitudes_excel(solicitudes_file)
                st.session_state["solicitudes_df"] = df_sol
                st.success(f"Cargadas {len(df_sol)} filas de Solicitudes 2025.")
            except Exception as exc:
                st.error(f"Error cargando Solicitudes 2025: {exc}")

    with col2:
        bbdd_file = st.file_uploader(
            "BBDD F10-02 (CSV)",
            type=["csv"],
            key="bbdd_informes",
        )
        if bbdd_file is not None:
            try:
                df_bbdd = data_loading.load_bbdd_csv(bbdd_file)
                df_bbdd = bbdd_logic.ensure_bbdd_columns(df_bbdd)
                st.session_state["bbdd_df"] = df_bbdd
                st.success(f"Cargadas {len(df_bbdd)} filas en la BBDD F10-02.")
            except Exception as exc:
                st.error(f"Error cargando BBDD F10-02: {exc}")

    with col3:
        jira_file = st.file_uploader(
            "Exportación Jira (CSV/Excel)",
            type=["csv", "xlsx", "xls"],
            key="jira_informes",
        )
        if jira_file is not None:
            try:
                df_jira = data_loading.load_jira_export(jira_file)
                st.session_state["jira_df"] = df_jira
                st.success(f"Cargadas {len(df_jira)} filas de Jira.")
            except Exception as exc:
                st.error(f"Error cargando Jira: {exc}")

    solicitudes_df: Optional[pd.DataFrame] = st.session_state.get("solicitudes_df")
    bbdd_df: pd.DataFrame = st.session_state.get("bbdd_df") or pd.DataFrame()
    jira_df: Optional[pd.DataFrame] = st.session_state.get("jira_df")

    if (
        solicitudes_df is None
        or solicitudes_df.empty
        or bbdd_df is None
        or bbdd_df.empty
    ):
        st.info(
            "Sube al menos **Solicitudes 2025** y la **BBDD F10-02** para continuar."
        )
        return

    st.markdown("---")
    st.subheader("1. Selección de Nº de Solicitud")

    col_num = "Nº Solicitud" if "Nº Solicitud" in solicitudes_df.columns else solicitudes_df.columns[0]
    solicitudes_unicas = (
        solicitudes_df[col_num].astype(str).dropna().unique().tolist()
    )
    solicitudes_unicas = sorted(solicitudes_unicas, key=lambda x: str(x))

    default_value = st.session_state.get("informe_num_solicitud") or (
        solicitudes_unicas[0] if solicitudes_unicas else ""
    )

    num_solicitud = st.selectbox(
        "Nº Solicitud",
        options=solicitudes_unicas,
        index=solicitudes_unicas.index(default_value)
        if default_value in solicitudes_unicas
        else 0,
    )
    st.session_state["informe_num_solicitud"] = num_solicitud

    # Vista previa cabecera
    mask_sol = solicitudes_df[col_num].astype(str) == str(num_solicitud)
    sol_row = solicitudes_df[mask_sol].iloc[0]

    with st.expander("Cabecera de diseño (Solicitudes 2025)", expanded=True):
        st.write(f"**Responsable:** {sol_row.get('Responsable', '')}")
        st.write(
            f"**Tipo:** {sol_row.get('Tipo', '')}  ·  "
            f"**Producto base:** {sol_row.get('Producto base', '')}"
        )
        st.write("**Descripción diseño:**")
        st.write(sol_row.get("Descripción diseño", ""))

    # Ensayos disponibles para esta solicitud
    bbdd_df = bbdd_logic.ensure_bbdd_columns(bbdd_df)
    df_bbdd_sel = bbdd_df[bbdd_df["Nº Solicitud"].astype(str) == str(num_solicitud)]

    if df_bbdd_sel.empty:
        st.warning(
            "No se han encontrado ensayos en la BBDD para este Nº de Solicitud."
        )
        return

    with st.expander("Ensayos / formulaciones (vista rápida BBDD)"):
        st.dataframe(df_bbdd_sel.head(200), use_container_width=True, height=260)

    # Selección de fórmula LIBERADA desde Jira
    jira_clave_liberada: Optional[str] = None
    if jira_df is not None and not jira_df.empty:
        st.subheader("2. Selección de fórmula LIBERADA (Jira)")

        # Solo issues cuyas claves aparezcan en los ID de ensayo de esta solicitud
        ids_ensayo = (
            df_bbdd_sel["ID ensayo"].astype(str).dropna().unique().tolist()
        )
        df_jira_rel = jira_df[
            jira_df["Clave de incidencia"].astype(str).isin(ids_ensayo)
        ].copy()

        df_jira_lib = jira_logic.find_liberado_candidates(df_jira_rel)

        if df_jira_rel.empty:
            st.info(
                "No se han encontrado issues Jira asociadas a los ID de ensayo de "
                "esta solicitud (por `Clave de incidencia`)."
            )
        else:
            with st.expander("Issues Jira asociadas a esta solicitud"):
                st.dataframe(
                    df_jira_rel[
                        [
                            "Clave de incidencia",
                            "Resumen",
                            "Estado",
                            "Persona asignada",
                        ]
                    ],
                    use_container_width=True,
                    height=260,
                )

        if not df_jira_lib.empty:
            opciones = [
                f"{row['Clave de incidencia']} · {row['Resumen']} ({row['Estado']})"
                for _, row in df_jira_lib.iterrows()
            ]
            claves = df_jira_lib["Clave de incidencia"].astype(str).tolist()

            idx_default = 0
            selected = st.selectbox(
                "Elige la formula LIBERADA que actuará como referencia (Fórmula OK):",
                options=opciones,
                index=idx_default,
            )
            jira_clave_liberada = claves[opciones.index(selected)]

            st.info(
                "Podrás seguir viendo el detalle de todos los ensayos en el informe; "
                "la issue LIBERADA se usará para rellenar campos de verificación."
            )
        else:
            st.warning(
                "No se han encontrado issues en estado LIBERADO para los ID de ensayo "
                "de esta solicitud. Se generará el informe sin información de LIBERADO."
            )

    # Construir InformeData y mostrar vista previa
    st.markdown("---")
    st.subheader("3. Vista previa del informe ISO")

    jira_df_for_report = jira_df if jira_df is not None else pd.DataFrame()
    informe: InformeData = report_builder.build_informe_data(
        df_solicitudes=solicitudes_df,
        df_bbdd=bbdd_df,
        df_jira=jira_df_for_report,
        numero_solicitud=str(num_solicitud),
        jira_clave_liberada=jira_clave_liberada,
    )

    _render_informe_preview(informe)

    # Descargas
    st.markdown("---")
    st.subheader("4. Exportar informe ISO")

    informe_csv_bytes = build_informe_iso_csv(informe)
    st.download_button(
        "📥 Descargar informe ISO (CSV maquetado)",
        data=informe_csv_bytes,
        file_name=f"Informe_{num_solicitud}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    wb = create_iso_workbook(informe)
    informe_xlsx_bytes = workbook_to_bytes(wb)
    st.download_button(
        "📥 Descargar informe ISO (Excel .xlsx)",
        data=informe_xlsx_bytes,
        file_name=f"Informe_{num_solicitud}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )


def _render_informe_preview(informe: InformeData) -> None:
    with st.expander("1. Datos de partida del diseño", expanded=True):
        st.write(f"**Responsable:** {informe.responsable}")
        st.write(
            f"**Nº Solicitud:** {informe.numero_solicitud}  ·  "
            f"**Tipo:** {informe.tipo_solicitud}"
        )
        st.write(f"**Producto base / línea:** {informe.producto_base}")
        st.write("**Descripción diseño:**")
        st.write(informe.descripcion_diseno)

    with st.expander("2. Ensayos / formulaciones", expanded=False):
        if not informe.ensayos:
            st.info("No hay ensayos registrados para esta solicitud.")
        else:
            for i, e in enumerate(informe.ensayos, start=1):
                etiqueta = f"Ensayo {i}: {e.id_ensayo} · {e.nombre_formulacion} ({e.resultado})"
                with st.expander(etiqueta, expanded=False):
                    st.write(
                        f"**Fecha ensayo:** {e.fecha_ensayo}  ·  "
                        f"**Resultado:** {e.resultado}"
                    )
                    if e.jira_estado or e.jira_persona_asignada:
                        st.write(
                            f"**Jira:** {e.jira_clave or ''} · "
                            f"{e.jira_estado or ''} · "
                            f"{e.jira_persona_asignada or ''}"
                        )
                    st.write("**Motivo / comentario:**")
                    st.write(e.motivo)
                    st.write("**Fórmula (materias primas):**")
                    df_formula = pd.DataFrame(
                        [
                            {"Materia prima": mp.nombre, "% peso": mp.porcentaje_peso}
                            for mp in e.materias
                        ]
                    )
                    st.dataframe(df_formula, use_container_width=True, height=220)

    with st.expander("3. Verificación y ANEXO F90-02", expanded=False):
        st.write(f"**Producto final:** {informe.producto_final}")
        st.write(f"**Fórmula OK:** {informe.formula_ok}")
        st.write(f"**Riquezas:** {informe.riquezas}")

        espec = informe.especificacion_final
        valid = informe.validacion_producto

        st.markdown("#### Especificación final")
        st.write(f"**Descripción:** {espec.descripcion}")
        st.write(
            f"**Aspecto:** {espec.aspecto}  ·  **Color:** {espec.color}  ·  "
            f"**Densidad:** {espec.densidad}  ·  **pH:** {espec.ph}"
        )
        st.write("**Características químicas:**")
        st.write(espec.caracteristicas_quimicas)

        st.markdown("#### Validación de producto")
        st.write(f"**Fecha de validación:** {valid.fecha_validacion}")
        st.write(f"**Comentario:** {valid.comentario_validacion}")


def _download_df_as_csv(df: pd.DataFrame, filename: str, label: str) -> None:
    csv_bytes = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


if __name__ == "__main__":  # pragma: no cover - ejecución directa
    main()

