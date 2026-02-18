"""
Exportación F10-03 (Validación producto): workbook generado por código (modo provisional).
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from models.solicitud import Solicitud


def build_f10_03_workbook(solicitud: Solicitud) -> Workbook:
    """Construye un workbook con la estructura F10-03 rellenada desde la solicitud."""
    wb = Workbook()
    ws = wb.active
    ws.title = "F10-03 Validación producto"
    p1 = solicitud.paso_1 or {}
    anexo = p1.get("anexo_f10_03") or {}
    esp = anexo.get("especificacion_final") or {}
    val = anexo.get("validacion") or {}
    filas: List[Dict[str, Any]] = val.get("filas") or []
    row = 1

    ws.cell(row, 1, "Responsable de proyecto:")
    ws.cell(row, 2, p1.get("responsable", ""))
    row += 1
    ws.cell(row, 1, "Nº Solicitud:")
    ws.cell(row, 2, str(solicitud.numero_solicitud_canonico))
    ws.cell(row, 3, "Tipo:")
    ws.cell(row, 4, p1.get("tipo", ""))
    row += 1
    ws.cell(row, 1, "Producto base / línea:")
    ws.cell(row, 2, p1.get("producto_base_linea", ""))
    row += 2

    ws.cell(row, 1, "1. ESPECIFICACIÓN FINAL")
    row += 1
    ws.cell(row, 1, "Descripción")
    ws.cell(row, 2, esp.get("descripcion", ""))
    row += 2
    ws.cell(row, 1, "Aspecto")
    ws.cell(row, 2, esp.get("aspecto", ""))
    row += 1
    ws.cell(row, 1, "Color")
    ws.cell(row, 2, esp.get("color", ""))
    row += 2
    ws.cell(row, 1, "Características químicas")
    ws.cell(row, 2, esp.get("caracteristicas_quimicas", ""))
    row += 2

    ws.cell(row, 1, "2. VALIDACIÓN")
    row += 1
    ws.cell(row, 1, "Fecha validación")
    ws.cell(row, 2, val.get("fecha_validacion", ""))
    row += 2
    ws.cell(row, 1, "Área")
    ws.cell(row, 2, "Aspecto a validar")
    ws.cell(row, 3, "OK/NOK")
    ws.cell(row, 4, "Comentarios")
    row += 1
    for f in filas:
        ws.cell(row, 1, str(f.get("area", "")))
        ws.cell(row, 2, str(f.get("aspecto_a_validar", "")))
        ws.cell(row, 3, str(f.get("validar_ok_nok", "")))
        ws.cell(row, 4, str(f.get("comentarios", "")))
        row += 1

    for col in range(1, 5):
        ws.column_dimensions[get_column_letter(col)].width = 25
    return wb


def build_f10_03_bytes(solicitud: Solicitud) -> bytes:
    """Devuelve el workbook F10-03 como bytes para descarga."""
    wb = build_f10_03_workbook(solicitud)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
