"""
App mínima: sidebar con selectbox de solicitud; área principal con F10-01 en bonito y JSON crudo.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import config
from exporters import (
    build_f10_01_bytes,
    build_f10_02_bytes,
    build_f10_02_bytes_all,
    build_f10_03_bytes,
    build_f10_03_bytes_all,
)

# Etiqueta amigable -> posibles claves en f10_01 (la primera = canónica al guardar)
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

SESSION_DATA_KEY = "solicitudes_data"


def _nombre_corto_archivo(solicitud: dict[str, Any], max_len: int = 35) -> str:
    """Nombre corto para archivos Excel: NOMBRE o NOM_COMERCIAL, limitado y sin caracteres problemáticos."""
    f01 = solicitud.get("f10_01") or {}
    raw = (f01.get("NOMBRE") or f01.get("NOM_COMERCIAL") or "solicitud")
    s = str(raw).strip() or "solicitud"
    if len(s) > max_len:
        s = s[:max_len]
    return "".join(c if c.isalnum() or c in ".-_" else "_" for c in s)


def _load_data_from_file(json_path: Path) -> dict[str, Any] | None:
    """Carga el JSON desde disco. Devuelve None si hay error."""
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_solicitudes_json() -> bool:
    """Persiste el data de session_state a config.DEFAULT_JSON_PATH. Devuelve True si OK."""
    data = st.session_state.get(SESSION_DATA_KEY)
    if not data or "solicitudes" not in data:
        return False
    json_path = config.DEFAULT_JSON_PATH
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _format_val(v: Any) -> str:
    if v is None or v == "":
        return "—"
    s = str(v).strip()
    if s.lower() in ("nan", "nat", "none"):
        return "—"
    return s


def _filter_car_quim_solo_mayor_cero(text: str) -> str:
    """Filtra líneas de características químicas dejando solo las con valor numérico > 0."""
    if not (text or text.strip()):
        return ""
    lines_out = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            lines_out.append(line)
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = line.split()
        if len(parts) >= 2:
            val_str = (parts[1] or "").strip().replace(",", ".")
            try:
                val = float(val_str)
                if val > 0:
                    lines_out.append(line)
            except ValueError:
                lines_out.append(line)
        else:
            lines_out.append(line)
    return "\n".join(lines_out)


def _row_val(row: dict[str, Any], label: str) -> str:
    keys = _F10_01_KEYS.get(label, (label,))
    for k in keys:
        if k in row:
            return _format_val(row.get(k))
    return "—"


def _render_f10_01(
    f01: dict[str, Any],
    solicitud_id: Any,
    numero_solicitud: str,
    key_prefix: str,
    solicitud: dict[str, Any],
) -> None:
    """Renderiza F10-01 editable y botón Guardar."""
    k = key_prefix
    f01 = f01 or {}
    st.subheader("F10-01 — Viabilidad y planificación de diseños")

    values: dict[str, str] = {}
    for label, keys_tuple in _F10_01_KEYS.items():
        canon = keys_tuple[0]
        val = str(f01.get(canon, "") or "").strip()
        values[canon] = val

    with st.expander("Identificación", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if solicitud_id is not None:
                st.metric("ID", solicitud_id)
            values["Nº Solicitud"] = st.text_input("Nº Solicitud", value=values.get("Nº Solicitud", ""), key=f"{k}_f01_num_sol")
            values["SOLICITANTE"] = st.text_input("Solicitante", value=values.get("SOLICITANTE", ""), key=f"{k}_f01_solicitante")
            values["NOMBRE"] = st.text_input("Nombre proyecto", value=values.get("NOMBRE", ""), key=f"{k}_f01_nombre")
        with c2:
            values["PAIS DESTINO"] = st.text_input("País destino", value=values.get("PAIS DESTINO", ""), key=f"{k}_f01_pais")
            acep = values.get("ACEPTADO", "") or "Sí"
            values["ACEPTADO"] = st.selectbox("Aceptado", ["Sí", "No"], index=0 if acep in ("Sí", "SÍ", "SI") else 1, key=f"{k}_f01_aceptado")
            fin = values.get("FINALIZADO", "") or "Sí"
            values["FINALIZADO"] = st.selectbox("Finalizado", ["Sí", "No"], index=0 if fin in ("Sí", "SÍ", "SI") else 1, key=f"{k}_f01_finalizado")

    with st.expander("Necesidad y contexto"):
        values["NECESIDAD"] = st.text_area("Necesidad", value=values.get("NECESIDAD", ""), height=100, key=f"{k}_f01_necesidad")
        values["VOLUMEN COMPETENCIA"] = st.text_input("Volumen competencia", value=values.get("VOLUMEN COMPETENCIA", ""), key=f"{k}_f01_vol_comp")
        values["PRECIO COMPETENCIA"] = st.text_input("Precio competencia", value=values.get("PRECIO COMPETENCIA", ""), key=f"{k}_f01_precio_comp")
        values["VOLUMEN PROPUESTO"] = st.text_input("Volumen propuesto", value=values.get("VOLUMEN PROPUESTO", ""), key=f"{k}_f01_vol_prop")
        values["ENVASE"] = st.text_input("Envase", value=values.get("ENVASE", ""), key=f"{k}_f01_envase")

    with st.expander("Planificación y fechas"):
        values["FECHA DE APROBACIÓN SOL."] = st.text_input("Fecha aprobación solicitud", value=values.get("FECHA DE APROBACIÓN SOL.", ""), key=f"{k}_f01_fecha_aprob")
        values["TIEMPO ESTIMADO (días laborables)"] = st.text_input("Tiempo estimado (días laborables)", value=values.get("TIEMPO ESTIMADO (días laborables)", ""), key=f"{k}_f01_tiempo_est")
        values["FECHA FINALIZACION ESTIMADA"] = st.text_input("Fecha finalización estimada", value=values.get("FECHA FINALIZACION ESTIMADA", ""), key=f"{k}_f01_fecha_fin_est")
        values["FECHA DE FINALIZACION REAL"] = st.text_input("Fecha finalización real", value=values.get("FECHA DE FINALIZACION REAL", ""), key=f"{k}_f01_fecha_fin_real")
        values["HORAS EMPLEADAS I+D"] = st.text_input("Horas empleadas I+D", value=values.get("HORAS EMPLEADAS I+D", ""), key=f"{k}_f01_horas_id")
        values["HORAS EMPLEADAS EN CALIDAD"] = st.text_input("Horas empleadas Calidad", value=values.get("HORAS EMPLEADAS EN CALIDAD", ""), key=f"{k}_f01_horas_cal")

    with st.expander("Motivo denegado"):
        values["MOTIVO DENEGADO"] = st.text_area("Motivo denegado", value=values.get("MOTIVO DENEGADO", ""), height=80, key=f"{k}_f01_motivo")

    with st.expander("Problemas y comentarios"):
        values["PROBLEMAS"] = st.text_area("Problemas", value=values.get("PROBLEMAS", ""), height=120, key=f"{k}_f01_problemas")
        values["COMENTARIOS"] = st.text_area("Comentarios", value=values.get("COMENTARIOS", ""), height=60, key=f"{k}_f01_comentarios")

    if st.button("Guardar F10-01", type="primary", key=f"{k}_f01_guardar"):
        new_f01 = {canon: (values.get(canon) or "").strip() for label, keys_tuple in _F10_01_KEYS.items() for canon in [keys_tuple[0]]}
        solicitud["f10_01"] = new_f01
        if _save_solicitudes_json():
            st.success("F10-01 guardado.")
            st.rerun()
        else:
            st.error("Error al guardar en disco.")


def _render_f10_02(f02: dict[str, Any], key_prefix: str, solicitud: dict[str, Any]) -> None:
    """Renderiza F10-02 editable: datos de partida, ensayos (sub-CRUD), verificación, Guardar."""
    k = key_prefix
    f02 = f02 or {}
    st.subheader("F10-02 — Diseño producto")

    with st.expander("1. Datos de partida del diseño", expanded=True):
        responsable = st.text_input("Responsable", value=str(f02.get("responsable") or ""), key=f"{k}_f02_resp")
        desc_partida = st.text_area("Descripción / datos de partida", value=str(f02.get("descripcion_partida_diseno") or ""), height=120, key=f"{k}_f02_desc")

    ensayos: list[dict[str, Any]] = list(f02.get("ensayos") or [])
    with st.expander("2. Ensayos / Formulación", expanded=True):
        for idx, e in enumerate(ensayos):
            eid = e.get("id") or ""
            nombre_ens = e.get("ensayo") or ""
            with st.expander(f"Ensayo: {eid} — {str(nombre_ens)[:50]}", expanded=False):
                e["id"] = st.text_input("ID", value=str(e.get("id") or ""), key=f"{k}_f02_e{idx}_id")
                e["ensayo"] = st.text_input("Nombre ensayo", value=str(e.get("ensayo") or ""), key=f"{k}_f02_e{idx}_ensayo")
                e["fecha"] = st.text_input("Fecha", value=str(e.get("fecha") or ""), key=f"{k}_f02_e{idx}_fecha")
                e["resultado"] = st.text_input("Resultado", value=str(e.get("resultado") or ""), key=f"{k}_f02_e{idx}_resultado")
                e["motivo_comentario"] = st.text_area("Motivo / comentario", value=str(e.get("motivo_comentario") or ""), height=80, key=f"{k}_f02_e{idx}_motivo")
                formula = e.get("formula") or [{"materia_prima": "", "porcentaje_peso": ""}]
                df = pd.DataFrame(formula)
                if df.empty or "materia_prima" not in df.columns:
                    df = pd.DataFrame([{"materia_prima": "", "porcentaje_peso": ""}])
                edited = st.data_editor(
                    df,
                    column_config={"materia_prima": "Materia prima", "porcentaje_peso": "% peso"},
                    num_rows="dynamic",
                    key=f"{k}_f02_e{idx}_formula",
                )
                e["formula"] = [{"materia_prima": str(r.get("materia_prima", "") or ""), "porcentaje_peso": str(r.get("porcentaje_peso", "") or "")} for r in edited.to_dict("records")]
                if st.button("Eliminar este ensayo", key=f"{k}_f02_e{idx}_del"):
                    ensayos.pop(idx)
                    solicitud["f10_02"] = solicitud.get("f10_02") or {}
                    solicitud["f10_02"]["ensayos"] = ensayos
                    _save_solicitudes_json()
                    st.rerun()
        if st.button("Añadir ensayo", key=f"{k}_f02_add_ensayo"):
            solicitud["f10_02"] = solicitud.get("f10_02") or {}
            ensayos.append({
                "id": "", "ensayo": "", "fecha": "", "resultado": "",
                "motivo_comentario": "", "formula": [{"materia_prima": "", "porcentaje_peso": ""}],
            })
            solicitud["f10_02"]["ensayos"] = ensayos
            _save_solicitudes_json()
            st.rerun()

    vd = f02.get("verificacion_diseno") or {}
    with st.expander("3. Verificación (Diseño)", expanded=True):
        producto_final = st.text_input("Producto final", value=str(vd.get("producto_final") or ""), key=f"{k}_f02_pf")
        formula_ok = st.text_input("Fórmula OK", value=str(vd.get("formula_ok") or ""), key=f"{k}_f02_fo")
        riquezas = st.text_area("Riquezas", value=str(vd.get("riquezas") or ""), height=100, key=f"{k}_f02_riq")

    if st.button("Guardar F10-02", type="primary", key=f"{k}_f02_guardar"):
        new_f02 = {
            "responsable": responsable.strip(),
            "descripcion_partida_diseno": desc_partida.strip(),
            "ensayos": [
                {
                    "id": (e.get("id") or "").strip(),
                    "ensayo": (e.get("ensayo") or "").strip(),
                    "fecha": (e.get("fecha") or "").strip(),
                    "resultado": (e.get("resultado") or "").strip(),
                    "motivo_comentario": (e.get("motivo_comentario") or "").strip(),
                    "formula": e.get("formula") or [],
                }
                for e in ensayos
            ],
            "verificacion_diseno": {
                "producto_final": producto_final.strip(),
                "formula_ok": formula_ok.strip(),
                "riquezas": riquezas.strip(),
            },
        }
        solicitud["f10_02"] = new_f02
        if _save_solicitudes_json():
            st.success("F10-02 guardado.")
            st.rerun()
        else:
            st.error("Error al guardar en disco.")


def _render_f10_03(f03: dict[str, Any], key_prefix: str, solicitud: dict[str, Any]) -> None:
    """Renderiza F10-03 editable: especificación final, validación (sub-CRUD filas), Guardar."""
    k = key_prefix
    f03 = f03 or {}
    st.subheader("F10-03 — Validación producto")

    esp = f03.get("especificacion_final") or {}
    with st.expander("1. Especificación final", expanded=True):
        descripcion = st.text_area("Descripción", value=str(esp.get("descripcion") or ""), height=120, key=f"{k}_f03_desc")
        aspecto = st.text_input("Aspecto", value=str(esp.get("aspecto") or ""), key=f"{k}_f03_aspecto")
        color = st.text_input("Color", value=str(esp.get("color") or ""), key=f"{k}_f03_color")
        car_quim = st.text_area("Características químicas", value=str(esp.get("caracteristicas_quimicas") or ""), height=150, key=f"{k}_f03_car_quim")
        solo_mayor_cero = st.checkbox("Mostrar solo parámetros > 0", value=False, key=f"{k}_f03_solo_mayor_cero")
        if solo_mayor_cero and (car_quim or "").strip():
            filtered = _filter_car_quim_solo_mayor_cero(car_quim)
            if filtered.strip():
                st.caption("Vista (solo parámetros con valor > 0):")
                st.code(filtered, language="text")
            else:
                st.caption("Ningún parámetro con valor > 0.")

    val = f03.get("validacion") or {}
    filas: list[dict[str, Any]] = list(val.get("filas") or [])
    with st.expander("2. Validación", expanded=True):
        fecha_validacion = st.text_input("Fecha validación", value=str(val.get("fecha_validacion") or ""), key=f"{k}_f03_fecha_val")
        for i, fila in enumerate(filas):
            with st.container():
                c1, c2, c3, c4 = st.columns([1, 2, 1, 2])
                with c1:
                    fila["area"] = st.text_input("Área", value=str(fila.get("area") or ""), key=f"{k}_f03_fila{i}_area")
                with c2:
                    fila["aspecto_a_validar"] = st.text_input("Aspecto a validar", value=str(fila.get("aspecto_a_validar") or ""), key=f"{k}_f03_fila{i}_aspecto")
                with c3:
                    oknok = (fila.get("validar_ok_nok") or "OK").strip().upper()
                    fila["validar_ok_nok"] = st.selectbox("OK/NOK", ["OK", "NOK"], index=0 if oknok == "OK" else 1, key=f"{k}_f03_fila{i}_oknok")
                with c4:
                    fila["comentarios"] = st.text_input("Comentarios", value=str(fila.get("comentarios") or ""), key=f"{k}_f03_fila{i}_com")
            if st.button("Eliminar fila", key=f"{k}_f03_fila{i}_del"):
                filas.pop(i)
                solicitud["f10_03"] = solicitud.get("f10_03") or {}
                (solicitud["f10_03"].setdefault("validacion", {}))["filas"] = filas
                _save_solicitudes_json()
                st.rerun()
        if st.button("Añadir fila de validación", key=f"{k}_f03_add_fila"):
            solicitud["f10_03"] = solicitud.get("f10_03") or {}
            v = solicitud["f10_03"].setdefault("validacion", {})
            filas.append({"area": "", "aspecto_a_validar": "", "validar_ok_nok": "OK", "comentarios": ""})
            v["filas"] = filas
            _save_solicitudes_json()
            st.rerun()

    if st.button("Guardar F10-03", type="primary", key=f"{k}_f03_guardar"):
        new_f03 = {
            "especificacion_final": {
                "descripcion": descripcion.strip(),
                "aspecto": aspecto.strip(),
                "color": color.strip(),
                "caracteristicas_quimicas": car_quim.strip(),
            },
            "validacion": {
                "fecha_validacion": fecha_validacion.strip(),
                "filas": [{"area": (f.get("area") or "").strip(), "aspecto_a_validar": (f.get("aspecto_a_validar") or "").strip(), "validar_ok_nok": (f.get("validar_ok_nok") or "OK").strip(), "comentarios": (f.get("comentarios") or "").strip()} for f in filas],
            },
        }
        solicitud["f10_03"] = new_f03
        if _save_solicitudes_json():
            st.success("F10-03 guardado.")
            st.rerun()
        else:
            st.error("Error al guardar en disco.")


def _render_delete_solicitud(solicitudes: list, selected_idx: int, key_prefix: str) -> None:
    """Botón Eliminar esta solicitud con confirmación en dos pasos."""
    confirm_key = f"confirm_delete_{key_prefix}"
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    if not st.session_state[confirm_key]:
        if st.button("Eliminar esta solicitud", type="secondary", key=f"{key_prefix}_del_sol_btn"):
            st.session_state[confirm_key] = True
            st.rerun()
        return
    st.warning("¿Eliminar esta solicitud? Esta acción no se puede deshacer.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirmar eliminación", type="primary", key=f"{key_prefix}_del_confirm"):
            st.session_state[confirm_key] = False
            solicitudes.pop(selected_idx)
            new_idx = min(selected_idx, len(solicitudes) - 1) if solicitudes else 0
            if solicitudes and "select_solicitud" in st.session_state:
                st.session_state["select_solicitud"] = new_idx
            if _save_solicitudes_json():
                st.success("Solicitud eliminada.")
            st.rerun()
    with col2:
        if st.button("Cancelar", key=f"{key_prefix}_del_cancel"):
            st.session_state[confirm_key] = False
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Solicitudes JSON", layout="wide")

    json_path = config.DEFAULT_JSON_PATH
    if not json_path.exists():
        st.warning(f"No se encuentra el JSON en {json_path}.")
        return

    # Estado en sesión: cargar una sola vez desde disco
    if SESSION_DATA_KEY not in st.session_state:
        data = _load_data_from_file(json_path)
        if data is None:
            st.error("Error al cargar JSON.")
            return
        st.session_state[SESSION_DATA_KEY] = data

    data = st.session_state[SESSION_DATA_KEY]
    solicitudes = data.get("solicitudes") or []
    if not solicitudes:
        st.info("El archivo no contiene solicitudes.")
        if st.sidebar.button("Recargar desde archivo"):
            if SESSION_DATA_KEY in st.session_state:
                del st.session_state[SESSION_DATA_KEY]
            st.rerun()
        if st.sidebar.button("Nueva solicitud"):
            new_sol = {
                "id": 1,
                "numero_solicitud": "",
                "f10_01": {},
                "f10_02": {"responsable": "", "descripcion_partida_diseno": "", "ensayos": [], "verificacion_diseno": {"producto_final": "", "formula_ok": "", "riquezas": ""}},
                "f10_03": {"especificacion_final": {"descripcion": "", "aspecto": "", "color": "", "caracteristicas_quimicas": ""}, "validacion": {"fecha_validacion": "", "filas": []}},
            }
            solicitudes.append(new_sol)
            if _save_solicitudes_json():
                st.session_state["select_solicitud"] = 0
                st.rerun()
        return

    # Sidebar: selectbox de solicitud + recargar + nueva solicitud
    st.sidebar.header("Solicitud")
    if st.sidebar.button("Recargar desde archivo"):
        if SESSION_DATA_KEY in st.session_state:
            del st.session_state[SESSION_DATA_KEY]
        st.rerun()
    if st.sidebar.button("Nueva solicitud"):
        new_id = 1
        if solicitudes:
            ids = [s.get("id") for s in solicitudes if isinstance(s, dict) and isinstance(s.get("id"), (int, float))]
            if ids:
                new_id = 1 + max(ids)
        new_sol = {
            "id": new_id,
            "numero_solicitud": "",
            "f10_01": {},
            "f10_02": {
                "responsable": "",
                "descripcion_partida_diseno": "",
                "ensayos": [],
                "verificacion_diseno": {"producto_final": "", "formula_ok": "", "riquezas": ""},
            },
            "f10_03": {
                "especificacion_final": {"descripcion": "", "aspecto": "", "color": "", "caracteristicas_quimicas": ""},
                "validacion": {"fecha_validacion": "", "filas": []},
            },
        }
        solicitudes.append(new_sol)
        if _save_solicitudes_json():
            st.session_state["select_solicitud"] = len(solicitudes) - 1
            st.success("Nueva solicitud creada.")
        st.rerun()
    items = [(s, f"{s.get('numero_solicitud') or '—'} (ID {s.get('id', '—')}) — {str((s.get('f10_01') or {}).get('NOMBRE') or (s.get('f10_01') or {}).get('NOM_COMERCIAL') or '—')[:50]}") for s in solicitudes if isinstance(s, dict)]
    if not items:
        st.info("No hay solicitudes válidas en el JSON.")
        return

    # Sidebar: Exportar F10-01 (todas)
    st.sidebar.header("Exportar")
    _ts = datetime.now().strftime("%Y%m%d_%H%M")
    if st.sidebar.button("Exportar F10-01 (todas)", key="export_f10_01_btn"):
        st.session_state["export_f10_01_bytes"] = build_f10_01_bytes(solicitudes)
        st.session_state["export_f10_01_filename"] = f"F10-01_Viabilidad_planificacion_2025_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    if st.session_state.get("export_f10_01_bytes"):
        st.sidebar.download_button(
            "Descargar F10-01",
            data=st.session_state["export_f10_01_bytes"],
            file_name=st.session_state.get("export_f10_01_filename", f"F10-01_Viabilidad_planificacion_2025_{_ts}.xlsx"),
            key="export_f10_01_dl",
        )
    if st.sidebar.button("Exportar todos F10-02", key="export_f10_02_all_btn"):
        st.session_state["export_f10_02_all_bytes"] = build_f10_02_bytes_all(solicitudes)
        st.session_state["export_f10_02_all_filename"] = f"F10-02_Todas_solicitudes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    if st.session_state.get("export_f10_02_all_bytes"):
        st.sidebar.download_button(
            "Descargar todos F10-02",
            data=st.session_state["export_f10_02_all_bytes"],
            file_name=st.session_state.get("export_f10_02_all_filename", f"F10-02_Todas_solicitudes_{_ts}.xlsx"),
            key="export_f10_02_all_dl",
        )
    if st.sidebar.button("Exportar todos F10-03", key="export_f10_03_all_btn"):
        st.session_state["export_f10_03_all_bytes"] = build_f10_03_bytes_all(solicitudes)
        st.session_state["export_f10_03_all_filename"] = f"F10-03_Todas_solicitudes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    if st.session_state.get("export_f10_03_all_bytes"):
        st.sidebar.download_button(
            "Descargar todos F10-03",
            data=st.session_state["export_f10_03_all_bytes"],
            file_name=st.session_state.get("export_f10_03_all_filename", f"F10-03_Todas_solicitudes_{_ts}.xlsx"),
            key="export_f10_03_all_dl",
        )

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

    widget_key_prefix = f"sid{sid}" if sid is not None else f"n{numero_solicitud}".replace(" ", "_").replace("/", "_")
    _render_delete_solicitud(solicitudes, selected_idx, widget_key_prefix)
    _render_f10_01(f01, sid, numero_solicitud, widget_key_prefix, solicitud)
    _render_f10_02(f02, widget_key_prefix, solicitud)
    _render_f10_03(f03, widget_key_prefix, solicitud)

    with st.expander("Exportar"):
        nombre_corto = _nombre_corto_archivo(solicitud)
        num_arch = (numero_solicitud or "sin_num").replace(" ", "_").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        # F10-02 (esta solicitud)
        if st.button("Generar F10-02", key=f"{widget_key_prefix}_export_f10_02_btn"):
            st.session_state[f"export_f10_02_bytes_{widget_key_prefix}"] = build_f10_02_bytes(solicitud)
            st.session_state[f"export_f10_02_filename_{widget_key_prefix}"] = f"F10-02_Solicitud_{num_arch}_{nombre_corto}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        if st.session_state.get(f"export_f10_02_bytes_{widget_key_prefix}"):
            st.download_button(
                "Descargar F10-02",
                data=st.session_state[f"export_f10_02_bytes_{widget_key_prefix}"],
                file_name=st.session_state.get(f"export_f10_02_filename_{widget_key_prefix}", f"F10-02_Solicitud_{num_arch}_{nombre_corto}_{ts}.xlsx"),
                key=f"{widget_key_prefix}_export_f10_02_dl",
            )
        st.caption("F10-02 — Diseño de producto (esta solicitud)")
        st.divider()
        # F10-03 (esta solicitud)
        if st.button("Generar F10-03", key=f"{widget_key_prefix}_export_f10_03_btn"):
            st.session_state[f"export_f10_03_bytes_{widget_key_prefix}"] = build_f10_03_bytes(solicitud)
            st.session_state[f"export_f10_03_filename_{widget_key_prefix}"] = f"F10-03_Solicitud_{num_arch}_{nombre_corto}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        if st.session_state.get(f"export_f10_03_bytes_{widget_key_prefix}"):
            st.download_button(
                "Descargar F10-03",
                data=st.session_state[f"export_f10_03_bytes_{widget_key_prefix}"],
                file_name=st.session_state.get(f"export_f10_03_filename_{widget_key_prefix}", f"F10-03_Solicitud_{num_arch}_{nombre_corto}_{ts}.xlsx"),
                key=f"{widget_key_prefix}_export_f10_03_dl",
            )
        st.caption("F10-03 — Validación de producto (esta solicitud)")

    with st.expander("JSON crudo (toda la solicitud)"):
        st.code(json.dumps(solicitud, indent=2, ensure_ascii=False), language="json")


if __name__ == "__main__":
    main()
