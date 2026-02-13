"""
Componentes Streamlit para el editor de solicitudes ISO.

Listado de solicitudes con buscador, detalle de solicitud (Paso 1 + ensayos),
panel de detalle de ensayo (resumen, fórmula editable, motivo, botones).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import pandas as pd
import streamlit as st

from .editor_data import (
    filter_empty_formula_rows,
    formula_to_tsv,
    parse_pasted_formula,
    validate_peso,
)


def _get_ensayo_safe(ensayo: Dict[str, Any]) -> tuple[List[Dict[str, Any]], str]:
    """Devuelve (formula, motivo_comentario) con valores por defecto si no existen."""
    formula = ensayo.get("formula")
    if formula is None:
        formula = []
    if not isinstance(formula, list):
        formula = []
    motivo = ensayo.get("motivo_comentario")
    if motivo is None:
        motivo = ""
    return formula, str(motivo)


def build_tabla_ensayos_flat(solicitudes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construye una lista plana de filas (una por ensayo) con columnas para vista general.
    Cada dict incluye solicitud_idx, ensayo_idx y campos para mostrar (numero_solicitud,
    producto, id_ensayo, resumen, formula_status, motivo_status).
    """
    rows: List[Dict[str, Any]] = []
    for sol_idx, s in enumerate(solicitudes):
        p1 = s.get("paso_1") or {}
        p2 = s.get("paso_2") or {}
        ensayos = p2.get("ensayos") or []
        num_sol = p1.get("numero_solicitud", "?")
        producto = (p1.get("producto_base_linea") or "")[:40]
        for ens_idx, e in enumerate(ensayos):
            formula, motivo = _get_ensayo_safe(e)
            formula_status = f"Sí ({len(formula)} líneas)" if formula else "No"
            motivo_status = "Sí" if (motivo or "").strip() else "No"
            resumen = (e.get("ensayo") or "")[:50]
            rows.append({
                "solicitud_idx": sol_idx,
                "ensayo_idx": ens_idx,
                "numero_solicitud": num_sol,
                "producto": producto,
                "id_ensayo": e.get("id", ""),
                "resumen": resumen,
                "formula_status": formula_status,
                "motivo_status": motivo_status,
            })
    return rows


def render_tabla_ensayos_flat(
    solicitudes: List[Dict[str, Any]],
    on_ir_a_editar: Callable[[int, int], None],
) -> None:
    """
    Muestra tabla plana de todos los ensayos y un selectbox + botón "Ir a editar"
    para abrir el panel de un ensayo concreto.
    """
    flat = build_tabla_ensayos_flat(solicitudes)
    if not flat:
        st.info("No hay ensayos para mostrar.")
        return
    df = pd.DataFrame([
        {
            "Nº Solicitud": r["numero_solicitud"],
            "Producto": r["producto"],
            "ID ensayo": r["id_ensayo"],
            "Resumen": r["resumen"],
            "Fórmula": r["formula_status"],
            "Motivo": r["motivo_status"],
        }
        for r in flat
    ])
    st.dataframe(df, use_container_width=True)
    options = [
        f"Solicitud {r['numero_solicitud']} · {r['id_ensayo']} — {r['resumen']}"
        for r in flat
    ]
    sel = st.selectbox(
        "Ir a editar este ensayo",
        range(len(flat)),
        format_func=lambda i: options[i],
        key="editor_flat_goto_select",
    )
    if st.button("Ir a editar", key="editor_flat_goto_btn"):
        row = flat[sel]
        on_ir_a_editar(row["solicitud_idx"], row["ensayo_idx"])


def render_listado_solicitudes(
    solicitudes: List[Dict[str, Any]],
    search_query: str,
    preselected_idx: int | None = None,
) -> int | None:
    """
    Renderiza la tabla/lista de solicitudes con buscador.
    Devuelve el índice de la fila seleccionada (si se usa selectbox/click) o None.
    preselected_idx: si se informa, el selectbox mostrará esa solicitud como seleccionada.
    """
    if not solicitudes:
        st.info("No hay solicitudes. Importa un JSON o genera primero.")
        return None

    filtered = solicitudes
    if search_query:
        q = search_query.strip().lower()
        filtered = []
        for s in solicitudes:
            p1 = s.get("paso_1") or {}
            num = str(p1.get("numero_solicitud", "")).lower()
            prod = str(p1.get("producto_base_linea", "")).lower()
            resp = str(p1.get("responsable", "")).lower()
            if q in num or q in prod or q in resp:
                filtered.append(s)

    if not filtered:
        st.warning("Ninguna solicitud coincide con la búsqueda.")
        return None

    options = []
    for i, s in enumerate(filtered):
        p1 = s.get("paso_1") or {}
        num = p1.get("numero_solicitud", "?")
        prod = (p1.get("producto_base_linea") or "")[:40]
        resp = p1.get("responsable", "")
        tipo = p1.get("tipo", "")
        options.append(f"{num} · {prod} · {resp} · {tipo}")

    index_default = 0
    if preselected_idx is not None and 0 <= preselected_idx < len(solicitudes):
        try:
            sel_sol = solicitudes[preselected_idx]
            index_default = filtered.index(sel_sol)
        except ValueError:
            pass

    idx_in_filtered = st.selectbox(
        "Selecciona una solicitud",
        range(len(filtered)),
        format_func=lambda i: options[i],
        index=index_default,
        key="editor_listado_select",
    )
    if idx_in_filtered is None:
        return None
    # Mapear índice en filtered de vuelta al índice en solicitudes
    selected_solicitud = filtered[idx_in_filtered]
    try:
        return solicitudes.index(selected_solicitud)
    except ValueError:
        return 0


def render_detalle_solicitud(
    solicitud: Dict[str, Any],
    solicitud_idx: int,
    preselected_ensayo_idx: int | None = None,
) -> int | None:
    """
    Renderiza el detalle de una solicitud: Paso 1 (solo lectura) y lista de ensayos.
    Devuelve el índice del ensayo seleccionado o None.
    preselected_ensayo_idx: si se informa, el selectbox mostrará ese ensayo como seleccionado.
    """
    p1 = solicitud.get("paso_1") or {}
    p2 = solicitud.get("paso_2") or {}
    ensayos = p2.get("ensayos") or []

    st.subheader("Paso 1 (solo lectura)")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Responsable:**", p1.get("responsable", ""))
        st.write("**Nº Solicitud:**", p1.get("numero_solicitud", ""))
        st.write("**Tipo:**", p1.get("tipo", ""))
    with col2:
        st.write("**Producto base / línea:**", p1.get("producto_base_linea", ""))
    st.write("**Descripción partida diseño:**", p1.get("descripcion_partida_diseno", ""))

    st.subheader("Ensayos")
    if not ensayos:
        st.info("No hay ensayos en esta solicitud.")
        return None

    options = [f"{e.get('id', '')} — {str(e.get('ensayo', ''))[:50]}" for e in ensayos]
    index_default = 0
    if preselected_ensayo_idx is not None and 0 <= preselected_ensayo_idx < len(ensayos):
        index_default = preselected_ensayo_idx
    ensayo_idx = st.selectbox(
        "Selecciona un ensayo",
        range(len(ensayos)),
        format_func=lambda i: options[i],
        index=index_default,
        key=f"editor_ensayo_select_{solicitud_idx}",
    )
    return ensayo_idx


def render_panel_ensayo(
    ensayo: Dict[str, Any],
    solicitud_idx: int,
    ensayo_idx: int,
    on_save: Callable[[Dict[str, Any]], None],
    on_revert: Callable[[], None],
    on_apply_paste: Callable[[List[Dict[str, Any]]], None] | None = None,
) -> None:
    """
    Renderiza el panel de detalle del ensayo: resumen (solo lectura), tabla fórmula,
    textarea motivo, botones Guardar / Revertir / Pegar fórmula / Copiar fórmula.
    on_save(ensayo_updated) y on_revert() son llamados al pulsar los botones.
    """
    st.subheader("Resumen del ensayo (solo lectura)")
    st.write("**ID:**", ensayo.get("id", ""))
    st.write("**Ensayo / Resumen:**", ensayo.get("ensayo", ""))
    st.write("**Fecha:**", ensayo.get("fecha", ""))
    st.write("**Resultado:**", ensayo.get("resultado", ""))

    formula, motivo = _get_ensayo_safe(ensayo)
    key_prefix = f"editor_ensayo_{solicitud_idx}_{ensayo_idx}"

    # Bloque fórmula
    st.subheader("Fórmula")
    with st.expander("Pegar fórmula", expanded=False):
        paste_area = st.text_area(
            "Pega líneas con Materia prima y % peso (separados por TAB o ;)",
            height=120,
            key=f"{key_prefix}_paste",
        )
        if st.button("Aplicar pegado", key=f"{key_prefix}_apply_paste"):
            parsed = parse_pasted_formula(paste_area)
            if parsed and on_apply_paste:
                on_apply_paste(parsed)
                st.rerun()

    if not formula:
        formula = [{"materia_prima": "", "porcentaje_peso": ""}]
    df = pd.DataFrame(formula)
    edited_df = st.data_editor(
        df,
        column_config={
            "materia_prima": st.column_config.TextColumn("Materia prima"),
            "porcentaje_peso": st.column_config.TextColumn("% peso"),
        },
        num_rows="dynamic",
        key=f"{key_prefix}_formula_editor",
    )
    st.caption("Usa el botón '+' al final de la tabla para añadir filas.")

    motivo_value = st.text_area(
        "Motivo / comentario",
        value=motivo,
        height=100,
        key=f"{key_prefix}_motivo",
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Guardar cambios", type="primary", key=f"{key_prefix}_save"):
            # Normalizar filas a materia_prima / porcentaje_peso y filtrar vacías
            raw_rows = edited_df.to_dict("records")
            rows = []
            for r in raw_rows:
                mp = str(r.get("materia_prima") or "").strip()
                pct = str(r.get("porcentaje_peso") or "").strip()
                rows.append({"materia_prima": mp, "porcentaje_peso": pct})
            rows = filter_empty_formula_rows(rows)
            invalid_peso = []
            for i, r in enumerate(rows):
                pct = (r.get("porcentaje_peso") or "").strip()
                if pct:
                    ok, _ = validate_peso(pct)
                    if not ok:
                        invalid_peso.append(i + 1)
            if invalid_peso:
                st.error(f"% peso no válido en fila(s): {invalid_peso}. Use número con coma o punto.")
            else:
                ensayo_updated = dict(ensayo)
                ensayo_updated["formula"] = rows
                motivo_str = (motivo_value or "").strip()
                if motivo_str:
                    ensayo_updated["motivo_comentario"] = motivo_str
                else:
                    ensayo_updated.pop("motivo_comentario", None)
                on_save(ensayo_updated)
    with col2:
        if st.button("Revertir", key=f"{key_prefix}_revert"):
            on_revert()
    with col3:
        tsv = formula_to_tsv(edited_df.to_dict("records"))
        if tsv:
            st.code(tsv, language=None)
            st.caption("Copia el contenido anterior al portapapeles (Ctrl+C) para pegarlo en Excel.")
