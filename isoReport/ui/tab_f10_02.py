"""
Tab F10-02: datos de partida, ensayos/formulación, verificación diseño. Edición + guardar.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import pandas as pd
import streamlit as st

from models.solicitud import Solicitud
from utils import (
    filter_empty_formula_rows,
    formula_to_tsv,
    parse_pasted_formula,
    validate_peso,
)


def render_tab_f10_02(
    solicitud: Solicitud,
    on_save: Callable[[Dict[str, Any], Dict[str, Any]], None],
    on_mark_unsaved: Callable[[], None],
) -> None:
    """Renderiza el tab F10-02 (diseño producto): edición y botón Guardar."""
    st.subheader("F10-02 — Diseño producto")

    if not solicitud.has_json_data():
        st.info("Inicializa esta solicitud en la bbdd desde el tab F10-01 o desde el listado para poder editar.")
        return

    p1 = dict(solicitud.paso_1)
    p2 = dict(solicitud.paso_2)
    if "verificacion_diseno" not in p1 or not isinstance(p1["verificacion_diseno"], dict):
        p1["verificacion_diseno"] = {"producto_final": "", "formula_ok": "", "riquezas": ""}
    v = p1["verificacion_diseno"]
    for k in ("producto_final", "formula_ok", "riquezas"):
        if k not in v:
            v[k] = ""

    # 1. Datos de partida
    with st.expander("1. Datos de partida del diseño", expanded=True):
        desc = st.text_area(
            "Descripción / datos de partida",
            value=p1.get("descripcion_partida_diseno") or "",
            height=150,
            key="f10_02_descripcion_partida",
        )
        p1["descripcion_partida_diseno"] = desc
        if desc != (solicitud.paso_1.get("descripcion_partida_diseno") or ""):
            on_mark_unsaved()

    # 2. Ensayos
    ensayos: List[Dict[str, Any]] = list(p2.get("ensayos") or [])
    with st.expander("2. Ensayos / Formulación", expanded=True):
        for ens_idx, ensayo in enumerate(ensayos):
            with st.expander(f"Ensayo: {ensayo.get('id', '')} — {str(ensayo.get('ensayo', ''))[:50]}", expanded=False):
                _render_ensayo_editor(solicitud, ensayo, ens_idx, ensayos, on_mark_unsaved)
        if st.button("Añadir ensayo", key="f10_02_add_ensayo"):
            ensayos.append({
                "id": "", "ensayo": "", "fecha": "", "resultado": "",
                "motivo_comentario": "", "formula": [{"materia_prima": "", "porcentaje_peso": ""}],
            })
            solicitud.paso_2["ensayos"] = ensayos
            on_mark_unsaved()
            st.rerun()
    p2["ensayos"] = ensayos
    solicitud.paso_2["ensayos"] = ensayos

    # 3. Verificación diseño
    with st.expander("3. Verificación (Diseño)", expanded=True):
        pf = st.text_input("Producto final", value=v.get("producto_final") or "", key="f10_02_producto_final")
        fo = st.text_input("Fórmula OK", value=v.get("formula_ok") or "", key="f10_02_formula_ok")
        riq = st.text_area("Riquezas", value=v.get("riquezas") or "", height=120, key="f10_02_riquezas")
        p1["verificacion_diseno"] = {"producto_final": pf, "formula_ok": fo, "riquezas": riq}
        if pf != v.get("producto_final") or fo != v.get("formula_ok") or riq != v.get("riquezas"):
            on_mark_unsaved()

    st.markdown("---")
    if st.button("Guardar cambios", type="primary", key="f10_02_guardar"):
        on_save(p1, p2)


def _render_ensayo_editor(
    solicitud: Solicitud,
    ensayo: Dict[str, Any],
    ens_idx: int,
    ensayos_list: List[Dict[str, Any]],
    on_mark_unsaved: Callable[[], None],
) -> None:
    prefix = f"f10_02_ens_{ens_idx}"
    ensayo["id"] = st.text_input("ID", value=ensayo.get("id") or "", key=f"{prefix}_id")
    ensayo["ensayo"] = st.text_input("Nombre ensayo", value=ensayo.get("ensayo") or "", key=f"{prefix}_ensayo")
    ensayo["fecha"] = st.text_input("Fecha", value=ensayo.get("fecha") or "", key=f"{prefix}_fecha")
    ensayo["resultado"] = st.text_input("Resultado", value=ensayo.get("resultado") or "", key=f"{prefix}_resultado")
    ensayo["motivo_comentario"] = st.text_area(
        "Motivo / comentario",
        value=ensayo.get("motivo_comentario") or "",
        height=80,
        key=f"{prefix}_motivo",
    )

    formula = ensayo.get("formula") or [{"materia_prima": "", "porcentaje_peso": ""}]
    with st.expander("Pegar fórmula (TAB o ;)"):
        paste_area = st.text_area("Pega líneas: materia prima TAB % peso", key=f"{prefix}_paste", height=100)
        if st.button("Aplicar pegado", key=f"{prefix}_apply_paste"):
            parsed = parse_pasted_formula(paste_area)
            if parsed:
                ensayo["formula"] = parsed
                on_mark_unsaved()
                st.rerun()

    df = pd.DataFrame(formula)
    edited_df = st.data_editor(
        df,
        column_config={
            "materia_prima": st.column_config.TextColumn("Materia prima"),
            "porcentaje_peso": st.column_config.TextColumn("% peso"),
        },
        num_rows="dynamic",
        key=f"{prefix}_formula",
    )
    rows = []
    for r in edited_df.to_dict("records"):
        rows.append({"materia_prima": str(r.get("materia_prima") or "").strip(), "porcentaje_peso": str(r.get("porcentaje_peso") or "").strip()})
    ensayo["formula"] = filter_empty_formula_rows(rows)

    if st.button("Eliminar este ensayo", key=f"{prefix}_del"):
        ensayos_list.pop(ens_idx)
        solicitud.paso_2["ensayos"] = ensayos_list
        on_mark_unsaved()
        st.rerun()
