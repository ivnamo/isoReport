"""
Conversión raw (paso_1/paso_2) <-> lista de solicitudes y estructura ANEXO F10-03.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .normalizers import normalize_numero_solicitud_for_match


def raw_to_solicitudes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convierte el JSON (paso_1[] + paso_2[]) en lista de solicitudes.
    Empareja por numero_solicitud y producto_base_linea.
    """
    paso_1_list = raw.get("paso_1") or []
    paso_2_list = raw.get("paso_2") or []
    if not paso_2_list:
        return [
            {
                "paso_1": p1,
                "paso_2": {
                    "ensayos": [],
                    "numero_solicitud": p1.get("numero_solicitud"),
                    "producto_base_linea": p1.get("producto_base_linea", ""),
                    "clave_incidencia_jira": "",
                },
            }
            for p1 in paso_1_list
        ]

    paso_2_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for blq in paso_2_list:
        num = normalize_numero_solicitud_for_match(blq.get("numero_solicitud"))
        prod = (str(blq.get("producto_base_linea") or "").strip())[:80]
        key = (num, prod)
        if key not in paso_2_by_key:
            paso_2_by_key[key] = blq

    result: List[Dict[str, Any]] = []
    for p1 in paso_1_list:
        num_norm = normalize_numero_solicitud_for_match(p1.get("numero_solicitud"))
        prod = (str(p1.get("producto_base_linea") or "").strip())[:80]
        p2 = paso_2_by_key.get((num_norm, prod))
        if p2 is None:
            for (n, _), blq in paso_2_by_key.items():
                if n == num_norm:
                    p2 = blq
                    break
        if p2 is None:
            p2 = {
                "ensayos": [],
                "numero_solicitud": p1.get("numero_solicitud"),
                "producto_base_linea": p1.get("producto_base_linea", ""),
                "clave_incidencia_jira": "",
            }
        result.append({"paso_1": p1, "paso_2": p2})
    return result


def solicitudes_to_raw(solicitudes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convierte la lista de solicitudes al formato raw (paso_1[] + paso_2[])."""
    paso_1 = [s["paso_1"] for s in solicitudes]
    paso_2 = [s["paso_2"] for s in solicitudes]
    return {"paso_1": paso_1, "paso_2": paso_2}


# ANEXO F10-03: 9 filas fijas de validación (validar_ok_nok = OK por defecto)
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


def ensure_anexo_f10_03(paso_1_item: Dict[str, Any]) -> None:
    """
    Asegura que paso_1_item tenga anexo_f10_03 con especificacion_final y validacion.filas.
    Modifica paso_1_item in-place.
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
    default_filas = ANEXO_F10_03_FILAS_VALIDACION
    while len(val["filas"]) < len(default_filas):
        idx = len(val["filas"])
        val["filas"].append({
            "area": default_filas[idx]["area"],
            "aspecto_a_validar": default_filas[idx]["aspecto_a_validar"],
            "validar_ok_nok": "OK",
            "comentarios": "",
        })
