"""
App mínima: sidebar con selectbox de solicitud; área principal con F10-01 en bonito y JSON crudo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

import config

# Etiqueta amigable -> posibles claves en f10_01 (la primera que exista se usa)
_F10_01_KEYS: dict[str, tuple[str, ...]] = {
    "Nº Solicitud": ("Nº Solicitud", "Nº solicitud"),
    "Solicitante": ("SOLICITANTE", "Solicitante"),
    "Nombre proyecto": ("NOMBRE", "NOM_COMERCIAL", "Nombre proyecto"),
    "País destino": ("PAIS DESTINO", "PAÍS DESTINO", "País destino"),
    "Aceptado": ("ACEPTADO", "Aceptado"),
    "Finalizado": ("FINALIZADO", "Finalizado"),
    "Necesidad": ("NECESIDAD", "Necesidad"),
    "Volumen competencia": ("VOLUMEN COMPETENCIA", "Volumen competencia"),
    "Precio competencia": ("PRECIO COMPETENCIA", "Precio competencia"),
    "Volumen propuesto": ("VOLUMEN PROPUESTO", "Volumen propuesto"),
    "Envase": ("ENVASE", "Envase"),
    "Fecha aprobación solicitud": ("FECHA DE APROBACIÓN SOL.", "FECHA DE APROBACION SOL.", "Fecha aprobación solicitud"),
    "Tiempo estimado (días laborables)": ("TIEMPO ESTIMADO (días laborables)", "Tiempo estimado (días laborables)"),
    "Fecha finalización estimada": ("FECHA FINALIZACION ESTIMADA", "Fecha finalización estimada"),
    "Fecha finalización real": ("FECHA DE FINALIZACION REAL", "FECHA FINALIZACION REAL", "Fecha finalización real"),
    "Horas empleadas I+D": ("HORAS EMPLEADAS I+D", "Horas empleadas I+D"),
    "Horas empleadas Calidad": ("HORAS EMPLEADAS EN CALIDAD", "Horas empleadas Calidad"),
    "Motivo denegado": ("MOTIVO DENEGADO", "Motivo denegado"),
    "Problemas": ("PROBLEMAS", "Problemas"),
    "Comentarios": ("COMENTARIOS", "Comentarios"),
}


def _format_val(v: Any) -> str:
    if v is None or v == "":
        return "—"
    s = str(v).strip()
    if s.lower() in ("nan", "nat", "none"):
        return "—"
    return s


def _row_val(row: dict[str, Any], label: str) -> str:
    keys = _F10_01_KEYS.get(label, (label,))
    for k in keys:
        if k in row:
            return _format_val(row.get(k))
    return "—"


def _render_f10_01(f01: dict[str, Any], solicitud_id: Any, numero_solicitud: str) -> None:
    """Muestra F10-01 en secciones legibles (solo lectura)."""
    if not f01:
        st.info("Esta solicitud no tiene datos F10-01.")
        return

    st.subheader("F10-01 — Viabilidad y planificación de diseños")
    st.caption("Solo lectura · datos del JSON")

    with st.expander("Identificación", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if solicitud_id is not None:
                st.metric("ID", solicitud_id)
            st.write("**Nº Solicitud:**", _row_val(f01, "Nº Solicitud"))
            st.write("**Solicitante:**", _row_val(f01, "Solicitante"))
            st.write("**Nombre proyecto:**", _row_val(f01, "Nombre proyecto"))
        with c2:
            st.write("**País destino:**", _row_val(f01, "País destino"))
            st.write("**Aceptado:**", _row_val(f01, "Aceptado"))
            st.write("**Finalizado:**", _row_val(f01, "Finalizado"))

    with st.expander("Necesidad y contexto"):
        st.write("**Necesidad:**", _row_val(f01, "Necesidad"))
        st.write("**Volumen competencia:**", _row_val(f01, "Volumen competencia"))
        st.write("**Precio competencia:**", _row_val(f01, "Precio competencia"))
        st.write("**Volumen propuesto:**", _row_val(f01, "Volumen propuesto"))
        st.write("**Envase:**", _row_val(f01, "Envase"))

    with st.expander("Planificación y fechas"):
        st.write("**Fecha aprobación solicitud:**", _row_val(f01, "Fecha aprobación solicitud"))
        st.write("**Tiempo estimado (días laborables):**", _row_val(f01, "Tiempo estimado (días laborables)"))
        st.write("**Fecha finalización estimada:**", _row_val(f01, "Fecha finalización estimada"))
        st.write("**Fecha finalización real:**", _row_val(f01, "Fecha finalización real"))
        st.write("**Horas empleadas I+D:**", _row_val(f01, "Horas empleadas I+D"))
        st.write("**Horas empleadas Calidad:**", _row_val(f01, "Horas empleadas Calidad"))

    with st.expander("Motivo denegado"):
        st.write(_row_val(f01, "Motivo denegado"))

    with st.expander("Problemas y comentarios"):
        st.write("**Problemas:**", _row_val(f01, "Problemas"))
        st.write("**Comentarios:**", _row_val(f01, "Comentarios"))


def _render_f10_02(f02: dict[str, Any]) -> None:
    """Muestra F10-02 en expanders: datos de partida, ensayos, verificación (solo lectura)."""
    if not f02:
        st.info("Esta solicitud no tiene datos F10-02.")
        return

    st.subheader("F10-02 — Diseño producto")
    st.caption("Solo lectura · datos del JSON")

    with st.expander("1. Datos de partida del diseño", expanded=True):
        resp = _format_val(f02.get("responsable"))
        desc = _format_val(f02.get("descripcion_partida_diseno"))
        st.write("**Responsable:**", resp)
        st.write("**Descripción / datos de partida:**")
        st.write(desc if desc != "—" else "")

    ensayos = f02.get("ensayos") or []
    with st.expander("2. Ensayos / Formulación", expanded=True):
        if not ensayos:
            st.write("— Sin ensayos registrados.")
        for i, e in enumerate(ensayos):
            eid = e.get("id") or "—"
            nombre_ensayo = e.get("ensayo") or "—"
            fecha = _format_val(e.get("fecha"))
            resultado = _format_val(e.get("resultado"))
            motivo = e.get("motivo_comentario") or "—"
            formula = e.get("formula") or []
            with st.expander(f"Ensayo: {eid} — {str(nombre_ensayo)[:55]}", expanded=False):
                st.write("**ID:**", eid)
                st.write("**Nombre:**", nombre_ensayo)
                st.write("**Fecha:**", fecha)
                st.write("**Resultado:**", resultado)
                st.write("**Motivo / comentario:**")
                st.write(motivo)
                if formula:
                    st.write("**Fórmula:**")
                    for fila in formula:
                        mp = fila.get("materia_prima") or ""
                        pp = fila.get("porcentaje_peso") or ""
                        if mp or pp:
                            st.write(f"- {mp}: {pp} %")

    vd = f02.get("verificacion_diseno") or {}
    with st.expander("3. Verificación (Diseño)", expanded=True):
        st.write("**Producto final:**", _format_val(vd.get("producto_final")))
        st.write("**Fórmula OK:**", _format_val(vd.get("formula_ok")))
        st.write("**Riquezas:**")
        st.write(_format_val(vd.get("riquezas")) if vd.get("riquezas") else "—")


def _render_f10_03(f03: dict[str, Any]) -> None:
    """Muestra F10-03 en expanders: especificación final y validación (solo lectura)."""
    if not f03:
        st.info("Esta solicitud no tiene datos F10-03.")
        return

    st.subheader("F10-03 — Validación producto")
    st.caption("Solo lectura · datos del JSON")

    esp = f03.get("especificacion_final") or {}
    with st.expander("1. Especificación final", expanded=True):
        st.write("**Descripción:**")
        st.write(_format_val(esp.get("descripcion")) if esp.get("descripcion") else "—")
        st.write("**Aspecto:**", _format_val(esp.get("aspecto")))
        st.write("**Color:**", _format_val(esp.get("color")))
        st.write("**Características químicas:**")
        car_quim = esp.get("caracteristicas_quimicas") or ""
        if car_quim:
            st.code(car_quim, language="text")
        else:
            st.write("—")

    val = f03.get("validacion") or {}
    with st.expander("2. Validación", expanded=True):
        st.write("**Fecha validación:**", _format_val(val.get("fecha_validacion")))
        filas = val.get("filas") or []
        if not filas:
            st.write("— Sin filas de validación.")
        else:
            for i, f in enumerate(filas):
                area = f.get("area") or "—"
                aspecto = f.get("aspecto_a_validar") or "—"
                ok_nok = f.get("validar_ok_nok") or "—"
                com = f.get("comentarios") or "—"
                st.write(f"**{i + 1}.** {area} · {aspecto} · **{ok_nok}**")
                if com != "—" and com:
                    st.caption(f"Comentarios: {com}")


def main() -> None:
    st.set_page_config(page_title="Solicitudes JSON", layout="wide")

    json_path = config.DEFAULT_JSON_PATH
    if not json_path.exists():
        st.warning(f"No se encuentra el JSON en {json_path}.")
        return

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Error al cargar JSON: {e}")
        return

    solicitudes = data.get("solicitudes") or []
    if not solicitudes:
        st.info("El archivo no contiene solicitudes.")
        return

    # Sidebar: solo selectbox de solicitud
    st.sidebar.header("Solicitud")
    items = [(s, f"{s.get('numero_solicitud') or '—'} (ID {s.get('id', '—')}) — {str((s.get('f10_01') or {}).get('NOMBRE') or (s.get('f10_01') or {}).get('NOM_COMERCIAL') or '—')[:50]}") for s in solicitudes if isinstance(s, dict)]
    if not items:
        st.info("No hay solicitudes válidas en el JSON.")
        return

    selected_idx = st.sidebar.selectbox(
        "Selecciona una solicitud",
        range(len(items)),
        format_func=lambda i: items[i][1],
        key="select_solicitud",
    )

    solicitud = items[selected_idx][0]
    f01 = solicitud.get("f10_01") or {}
    f02 = solicitud.get("f10_02") or {}
    f03 = solicitud.get("f10_03") or {}
    numero_solicitud = solicitud.get("numero_solicitud") or "—"
    sid = solicitud.get("id")
    nom = f01.get("NOMBRE") or f01.get("NOM_COMERCIAL") or "—"

    st.title(f"Solicitud {numero_solicitud} — {str(nom)[:60]}")
    if sid is not None:
        st.caption(f"ID {sid}")

    _render_f10_01(f01, sid, numero_solicitud)
    _render_f10_02(f02)
    _render_f10_03(f03)

    with st.expander("JSON crudo (toda la solicitud)"):
        st.code(json.dumps(solicitud, indent=2, ensure_ascii=False), language="json")


if __name__ == "__main__":
    main()
