"""
Capa de datos del editor de solicitudes ISO.

Transformación entre formato raw (paso_1[] + paso_2[]) y lista de solicitudes;
carga/guardado en disco; parseo de fórmula pegado; validación de % peso.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from iso_reports.paso1 import _normalize_id_for_match


DEFAULT_JSON_PATH = "data/solicitudes.json"


def _normalize_numero_solicitud_for_match(value: Any) -> str:
    """Valor canónico para comparar numero_solicitud (1, '1', 1.0 -> '1')."""
    if value is None:
        return ""
    s = str(value).strip()
    try:
        n = int(float(s))
        return str(n)
    except (ValueError, TypeError):
        return s


def raw_to_solicitudes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convierte el JSON generado por la app (paso_1[] + paso_2[]) en lista de solicitudes.
    Empareja por numero_solicitud (y producto_base_linea si hay varios) para que el orden
    distinto entre paso_1 y paso_2 en el JSON no mezcle productos con ensayos de otra solicitud.
    """
    paso_1_list = raw.get("paso_1") or []
    paso_2_list = raw.get("paso_2") or []
    if not paso_2_list:
        return [{"paso_1": p1, "paso_2": {"ensayos": [], "numero_solicitud": p1.get("numero_solicitud"), "producto_base_linea": p1.get("producto_base_linea", ""), "clave_incidencia_jira": ""}} for p1 in paso_1_list]

    # Índice: (num_sol_norm, producto_norm) -> paso_2 block (usar el primero si hay duplicados)
    paso_2_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for blq in paso_2_list:
        num = _normalize_numero_solicitud_for_match(blq.get("numero_solicitud"))
        prod = (str(blq.get("producto_base_linea") or "").strip())[:80]
        key = (num, prod)
        if key not in paso_2_by_key:
            paso_2_by_key[key] = blq

    result: List[Dict[str, Any]] = []
    for p1 in paso_1_list:
        num_norm = _normalize_numero_solicitud_for_match(p1.get("numero_solicitud"))
        prod = (str(p1.get("producto_base_linea") or "").strip())[:80]
        p2 = paso_2_by_key.get((num_norm, prod))
        if p2 is None:
            # Fallback: mismo numero_solicitud, cualquier producto
            for (n, _), blq in paso_2_by_key.items():
                if n == num_norm:
                    p2 = blq
                    break
        if p2 is None:
            p2 = {"ensayos": [], "numero_solicitud": p1.get("numero_solicitud"), "producto_base_linea": p1.get("producto_base_linea", ""), "clave_incidencia_jira": ""}
        result.append({"paso_1": p1, "paso_2": p2})
    return result


def solicitudes_to_raw(solicitudes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convierte la lista de solicitudes de vuelta al formato raw (paso_1[] + paso_2[])
    para compatibilidad con el generador y guardado en disco.
    """
    paso_1 = [s["paso_1"] for s in solicitudes]
    paso_2 = [s["paso_2"] for s in solicitudes]
    return {"paso_1": paso_1, "paso_2": paso_2}


def load_solicitudes_json(path: str | Path) -> List[Dict[str, Any]]:
    """
    Carga el JSON desde disco y devuelve la lista de solicitudes.
    Si el fichero no existe o está vacío, devuelve [].
    Aplica auto-relleno de verificación (producto_final, formula_ok) desde paso_2 cuando hay LIBERADO.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    solicitudes = raw_to_solicitudes(raw)
    autorellenar_verificacion_desde_paso2_liberado(solicitudes)
    return solicitudes


def save_solicitudes_json(path: str | Path, solicitudes: List[Dict[str, Any]]) -> None:
    """
    Guarda la lista de solicitudes en disco en formato raw.
    Crea la carpeta padre si no existe.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = solicitudes_to_raw(solicitudes)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def parse_pasted_formula(text: str) -> List[Dict[str, str]]:
    """
    Parsea texto pegado (TAB o ; como separador) en filas de fórmula.
    - Trim por línea; ignora líneas vacías.
    - Cada línea: materia_prima, porcentaje_peso (si falta %, se deja vacío).
    """
    rows: List[Dict[str, str]] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t", 1)]
        elif ";" in line:
            parts = [p.strip() for p in line.split(";", 1)]
        else:
            parts = [line.strip(), ""]
        materia = parts[0] if len(parts) > 0 else ""
        pct = parts[1] if len(parts) > 1 else ""
        rows.append({"materia_prima": materia, "porcentaje_peso": pct})
    return rows


# Regex: número con coma o punto decimal (opcional)
_PESO_PATTERN = re.compile(r"^\s*-?\d+([,.]\d+)?\s*$")


def validate_peso(value: str) -> Tuple[bool, str]:
    """
    Valida que value sea un número aceptable (coma o punto como decimal).
    Devuelve (True, "") si es válido, (False, mensaje_error) si no.
    """
    if value is None:
        return True, ""
    s = str(value).strip()
    if not s:
        return True, ""
    s_normalized = s.replace(",", ".")
    if _PESO_PATTERN.match(s) or _PESO_PATTERN.match(s_normalized):
        return True, ""
    return False, "El valor debe ser un número (coma o punto como decimal)."


def filter_empty_formula_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filtra filas donde materia_prima y porcentaje_peso estén ambos vacíos.
    """
    return [
        r
        for r in rows
        if (r.get("materia_prima") or "").strip() or (r.get("porcentaje_peso") or "").strip()
    ]


def formula_to_tsv(formula: List[Dict[str, Any]]) -> str:
    """Convierte la lista de fórmula a texto TSV (Materia prima TAB % peso) para copiar."""
    lines = []
    for row in formula:
        mp = (row.get("materia_prima") or "").strip()
        pct = (row.get("porcentaje_peso") or "").strip()
        lines.append(f"{mp}\t{pct}")
    return "\n".join(lines)


# Columnas del CSV BBDD para verificación diseño (enriquecimiento)
VERIF_COL_ID_ENSAYO = "ID ensayo"
VERIF_COL_PRODUCTO_FINAL = "Producto final"
VERIF_COL_FORMULA_OK = "Fórmula OK"
VERIF_COL_RIQUEZAS = "Riquezas"
VERIF_COL_RESULTADO = "Resultado"
VERIF_RESULTADO_LIBERADO = "LIBERADO"


def get_id_ensayo_from_paso1_item(paso_1_item: Dict[str, Any]) -> str:
    """
    Obtiene el ID de ensayo desde un elemento de paso_1.
    Soporta formato plano (mapeo_id_ensayo_detectado) y anidado (mapeo.id_ensayo_detectado).
    """
    if not paso_1_item:
        return ""
    flat = paso_1_item.get("mapeo_id_ensayo_detectado")
    if flat is not None and str(flat).strip():
        return str(flat).strip()
    mapeo = paso_1_item.get("mapeo") or {}
    return str(mapeo.get("id_ensayo_detectado", "") or "").strip()


def get_id_formula_ok_from_paso1_item(paso_1_item: Dict[str, Any]) -> str:
    """
    Obtiene el ID de la fórmula liberada desde verificacion_diseno.formula_ok.
    El formato es "ID-xxx || nombre formulación"; devuelve la parte antes de " || " (trimmed).
    Si no hay " || ", devuelve cadena vacía (o el valor completo si se prefiere; aquí vacío por coherencia).
    """
    if not paso_1_item:
        return ""
    v = paso_1_item.get("verificacion_diseno")
    if not isinstance(v, dict):
        return ""
    fo = (v.get("formula_ok") or "").strip()
    if " || " in fo:
        return fo.split(" || ", 1)[0].strip()
    return ""


def get_id_ensayos_liberados_from_paso1_item(paso_1_item: Dict[str, Any]) -> List[str]:
    """
    Obtiene la lista de ID ensayos liberados desde un elemento de paso_1.
    Soporta formato plano (mapeo_id_ensayos_liberados) y anidado (mapeo.id_ensayos_liberados).
    Devuelve lista vacía si no existe o tiene 0 o 1 elemento (solo se persiste cuando hay varios).
    """
    if not paso_1_item:
        return []
    flat = paso_1_item.get("mapeo_id_ensayos_liberados")
    if isinstance(flat, list):
        return [str(x).strip() for x in flat if x is not None and str(x).strip()]
    mapeo = paso_1_item.get("mapeo") or {}
    ids = mapeo.get("id_ensayos_liberados")
    if isinstance(ids, list):
        return [str(x).strip() for x in ids if x is not None and str(x).strip()]
    return []


def _ensure_verificacion_diseno(paso_1_item: Dict[str, Any]) -> None:
    """Asegura que paso_1_item tenga verificacion_diseno con las tres claves."""
    if "verificacion_diseno" not in paso_1_item or not isinstance(paso_1_item["verificacion_diseno"], dict):
        paso_1_item["verificacion_diseno"] = {
            "producto_final": "",
            "formula_ok": "",
            "riquezas": "",
        }
    v = paso_1_item["verificacion_diseno"]
    for key in ("producto_final", "formula_ok", "riquezas"):
        if key not in v:
            v[key] = ""


# ANEXO F10-03: 9 filas fijas de validación (VALIDAR por defecto OK)
ANEXO_F10_03_FILAS_VALIDACION: List[Dict[str, Any]] = [
    {"area": "I+D+i", "aspecto_a_validar": "Fórmula - Funcionalidad", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Técnico", "aspecto_a_validar": "Validación agronómica", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Registros", "aspecto_a_validar": "Cumplimiento legislativo", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Producción", "aspecto_a_validar": "Viabilidad productiva", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Calidad", "aspecto_a_validar": "Cumplimiento legislativo", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Calidad", "aspecto_a_validar": "Composición declarada", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Calidad", "aspecto_a_validar": "Estabilidad química", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Marketing y/o Dirección", "aspecto_a_validar": "Precio Tarifa", "validar_ok_nok": "OK", "comentarios": ""},
    {"area": "Marketing y/o Dirección", "aspecto_a_validar": "Lanzamiento", "validar_ok_nok": "OK", "comentarios": ""},
]


def _ensure_anexo_f10_03(paso_1_item: Dict[str, Any]) -> None:
    """
    Asegura que paso_1_item tenga anexo_f10_03 con especificacion_final y validacion.filas.
    Si no existe, crea la estructura con las 9 filas por defecto (validar_ok_nok = OK).
    Si ya existe pero faltan filas, completa sin sobrescribir valores guardados.
    """
    if "anexo_f10_03" not in paso_1_item or not isinstance(paso_1_item["anexo_f10_03"], dict):
        paso_1_item["anexo_f10_03"] = {
            "especificacion_final": {
                "descripcion": "",
                "aspecto": "",
                "densidad": "",
                "color": "",
                "ph": "",
                "caracteristicas_quimicas": "",
            },
            "validacion": {
                "fecha_validacion": "",
                "filas": [dict(f) for f in ANEXO_F10_03_FILAS_VALIDACION],
            },
        }
        return
    a = paso_1_item["anexo_f10_03"]
    if "especificacion_final" not in a or not isinstance(a["especificacion_final"], dict):
        a["especificacion_final"] = {
            "descripcion": "", "aspecto": "", "densidad": "", "color": "", "ph": "", "caracteristicas_quimicas": "",
        }
    esp = a["especificacion_final"]
    for key in ("descripcion", "aspecto", "densidad", "color", "ph", "caracteristicas_quimicas"):
        if key not in esp:
            esp[key] = ""
    if "validacion" not in a or not isinstance(a["validacion"], dict):
        a["validacion"] = {"fecha_validacion": "", "filas": [dict(f) for f in ANEXO_F10_03_FILAS_VALIDACION]}
        return
    val = a["validacion"]
    if "fecha_validacion" not in val:
        val["fecha_validacion"] = ""
    if "filas" not in val or not isinstance(val["filas"], list):
        val["filas"] = [dict(f) for f in ANEXO_F10_03_FILAS_VALIDACION]
        return
    # Completar hasta 9 filas si faltan; nuevas filas con default OK
    default_filas = ANEXO_F10_03_FILAS_VALIDACION
    while len(val["filas"]) < len(default_filas):
        idx = len(val["filas"])
        val["filas"].append({
            "area": default_filas[idx]["area"],
            "aspecto_a_validar": default_filas[idx]["aspecto_a_validar"],
            "validar_ok_nok": "OK",
            "comentarios": "",
        })


def build_solicitudes_listas_validacion_producto(
    solicitudes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Devuelve solicitudes listas para el formulario ANEXO F10-03: tienen al menos un ensayo
    con resultado LIBERADO y verificación de diseño completa (producto_final, formula_ok, riquezas no vacíos).
    Cada elemento: solicitud_idx, paso_1.
    """
    result: List[Dict[str, Any]] = []
    for sol_idx, s in enumerate(solicitudes):
        p2 = s.get("paso_2") or {}
        ensayos = p2.get("ensayos") or []
        tiene_liberado = any(
            str(e.get("resultado", "") or "").strip().upper() == VERIF_RESULTADO_LIBERADO.upper()
            for e in ensayos
        )
        if not tiene_liberado:
            continue
        p1 = s.get("paso_1") or {}
        v = p1.get("verificacion_diseno")
        if not isinstance(v, dict):
            continue
        pf = (v.get("producto_final") or "").strip()
        fo = (v.get("formula_ok") or "").strip()
        riq = (v.get("riquezas") or "").strip()
        if pf and fo and riq:
            result.append({"solicitud_idx": sol_idx, "paso_1": p1})
    return result


def autorellenar_verificacion_desde_paso2_liberado(
    solicitudes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Rellena automáticamente producto_final y formula_ok en verificacion_diseno cuando
    en paso_2 hay al menos un ensayo con resultado LIBERADO.
    - Producto final = paso_1.producto_base_linea
    - Fórmula OK = "{id} || {ensayo}" del ensayo liberado (preferir el que coincida con id_ensayo de paso_1).
    No modifica riquezas. Modifica in-place y devuelve la misma lista.
    """
    if not solicitudes:
        return solicitudes
    for sol in solicitudes:
        paso_1 = sol.get("paso_1") or {}
        paso_2 = sol.get("paso_2") or {}
        ensayos = paso_2.get("ensayos") or []
        liberados = [
            e for e in ensayos
            if str(e.get("resultado", "") or "").strip().upper() == VERIF_RESULTADO_LIBERADO.upper()
        ]
        if not liberados:
            _ensure_verificacion_diseno(paso_1)
            continue
        id_ensayo = get_id_ensayo_from_paso1_item(paso_1)
        id_norm = _normalize_id_for_match(id_ensayo)
        elegido = None
        for e in liberados:
            if id_norm and _normalize_id_for_match(str(e.get("id") or "")) == id_norm:
                elegido = e
                break
        if elegido is None:
            elegido = liberados[0]
        _ensure_verificacion_diseno(paso_1)
        v = paso_1["verificacion_diseno"]
        v["producto_final"] = str(paso_1.get("producto_base_linea") or "").strip()
        e_id = str(elegido.get("id") or "").strip()
        e_ensayo = str(elegido.get("ensayo") or "").strip()
        v["formula_ok"] = f"{e_id} || {e_ensayo}" if (e_id or e_ensayo) else ""
    return solicitudes


def enriquecer_verificacion_diseno_desde_csv(
    solicitudes: List[Dict[str, Any]],
    df_bbdd: Any,
) -> List[Dict[str, Any]]:
    """
    Enriquece verificacion_diseno de cada paso_1 haciendo join por ID ensayo (normalizado).
    df_bbdd debe tener columnas "ID ensayo", y opcionalmente "Producto final", "Fórmula OK", "Riquezas".
    Si falta alguna columna, no falla y rellena solo las presentes.
    Modifica los elementos de solicitudes in-place y devuelve la misma lista.
    """
    import pandas as pd

    if not solicitudes or df_bbdd is None or (hasattr(df_bbdd, "empty") and df_bbdd.empty):
        return solicitudes

    col_id = VERIF_COL_ID_ENSAYO
    if col_id not in df_bbdd.columns:
        return solicitudes

    # Si existe columna Resultado, filtrar solo filas LIBERADO
    work = df_bbdd
    if VERIF_COL_RESULTADO in df_bbdd.columns:
        mask = (
            df_bbdd[VERIF_COL_RESULTADO]
            .astype(str)
            .str.strip()
            .str.upper()
            == VERIF_RESULTADO_LIBERADO.upper()
        )
        work = df_bbdd[mask].copy()

    # Índice normalizado -> primera fila que tiene ese ID (representante; si hay varias por ID, primera por orden)
    id_to_row: Dict[str, pd.Series] = {}
    for idx, row in work.iterrows():
        raw_id = row.get(col_id)
        nid = _normalize_id_for_match(str(raw_id) if raw_id is not None else "")
        if nid and nid not in id_to_row:
            id_to_row[nid] = row

    for sol in solicitudes:
        paso_1 = sol.get("paso_1") or {}
        id_ensayo = get_id_ensayo_from_paso1_item(paso_1)
        nid = _normalize_id_for_match(id_ensayo)
        if not nid or nid not in id_to_row:
            _ensure_verificacion_diseno(paso_1)
            continue
        row = id_to_row[nid]
        _ensure_verificacion_diseno(paso_1)
        v = paso_1["verificacion_diseno"]
        if VERIF_COL_PRODUCTO_FINAL in df_bbdd.columns:
            val = row.get(VERIF_COL_PRODUCTO_FINAL)
            v["producto_final"] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else ""
        if VERIF_COL_FORMULA_OK in df_bbdd.columns:
            val = row.get(VERIF_COL_FORMULA_OK)
            v["formula_ok"] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else ""
        if VERIF_COL_RIQUEZAS in df_bbdd.columns:
            val = row.get(VERIF_COL_RIQUEZAS)
            v["riquezas"] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else ""

    return solicitudes
