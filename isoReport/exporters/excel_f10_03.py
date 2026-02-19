"""
Exportación F10-03 (Validación producto): workbook generado desde dict de solicitud, con formato legible.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SECTION_FILL = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
SECTION_FONT = Font(bold=True, size=12)
TITLE_FONT = Font(bold=True, size=14)
LABEL_FONT = Font(bold=True)
WRAP_ALIGNMENT = Alignment(wrap_text=True, vertical="top")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def _producto_nombre(solicitud: dict[str, Any]) -> str:
    f01 = solicitud.get("f10_01") or {}
    return (f01.get("NOMBRE") or f01.get("NOM_COMERCIAL") or "").strip() or "—"


def _responsable(solicitud: dict[str, Any]) -> str:
    f02 = solicitud.get("f10_02") or {}
    return (f02.get("responsable") or "").strip()


def build_f10_03_workbook(solicitud: dict[str, Any]) -> Workbook:
    """Construye un workbook F10-03 rellenado desde el dict (f10_03, f10_01, f10_02)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "F10-03 Validación producto"

    f03 = solicitud.get("f10_03") or {}
    esp = f03.get("especificacion_final") or {}
    val = f03.get("validacion") or {}
    filas: List[Dict[str, Any]] = val.get("filas") or []

    numero = solicitud.get("numero_solicitud") or ""
    producto = _producto_nombre(solicitud)
    responsable = _responsable(solicitud)

    row = 1

    # Título
    ws.cell(row, 1, "F10-03 — Validación de producto")
    ws.cell(row, 1).font = TITLE_FONT
    row += 2

    # Identificación
    ws.cell(row, 1, "Nº Solicitud:")
    ws.cell(row, 1).font = LABEL_FONT
    ws.cell(row, 2, str(numero))
    row += 1
    ws.cell(row, 1, "Responsable:")
    ws.cell(row, 1).font = LABEL_FONT
    ws.cell(row, 2, str(responsable))
    row += 1
    ws.cell(row, 1, "Producto:")
    ws.cell(row, 1).font = LABEL_FONT
    ws.cell(row, 2, producto)
    row += 2

    # 1. ESPECIFICACIÓN FINAL
    ws.cell(row, 1, "1. ESPECIFICACIÓN FINAL")
    ws.cell(row, 1).font = SECTION_FONT
    ws.cell(row, 1).fill = SECTION_FILL
    row += 1
    ws.cell(row, 1, "Descripción")
    ws.cell(row, 1).font = LABEL_FONT
    desc_cell = ws.cell(row, 2, esp.get("descripcion", ""))
    desc_cell.alignment = WRAP_ALIGNMENT
    row += 2
    ws.cell(row, 1, "Aspecto")
    ws.cell(row, 1).font = LABEL_FONT
    ws.cell(row, 2, esp.get("aspecto", ""))
    row += 1
    ws.cell(row, 1, "Color")
    ws.cell(row, 1).font = LABEL_FONT
    ws.cell(row, 2, esp.get("color", ""))
    row += 2
    ws.cell(row, 1, "Características químicas")
    ws.cell(row, 1).font = LABEL_FONT
    quim_cell = ws.cell(row, 2, esp.get("caracteristicas_quimicas", ""))
    quim_cell.alignment = WRAP_ALIGNMENT
    row += 2

    # 2. VALIDACIÓN
    ws.cell(row, 1, "2. VALIDACIÓN")
    ws.cell(row, 1).font = SECTION_FONT
    ws.cell(row, 1).fill = SECTION_FILL
    row += 1
    ws.cell(row, 1, "Fecha validación")
    ws.cell(row, 1).font = LABEL_FONT
    ws.cell(row, 2, val.get("fecha_validacion", ""))
    row += 2
    # Tabla: Área, Aspecto a validar, OK/NOK, Comentarios
    headers = ["Área", "Aspecto a validar", "OK/NOK", "Comentarios"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row, col, h)
        cell.font = LABEL_FONT
        cell.fill = SECTION_FILL
        cell.border = THIN_BORDER
    row += 1
    for f in filas:
        ws.cell(row, 1, str(f.get("area", ""))).border = THIN_BORDER
        ws.cell(row, 2, str(f.get("aspecto_a_validar", ""))).border = THIN_BORDER
        ws.cell(row, 3, str(f.get("validar_ok_nok", ""))).border = THIN_BORDER
        com_cell = ws.cell(row, 4, str(f.get("comentarios", "")))
        com_cell.border = THIN_BORDER
        com_cell.alignment = WRAP_ALIGNMENT
        row += 1

    # Anchos: ~20, ~35, ~10, ~25
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 25
    return wb


def build_f10_03_bytes(solicitud: dict[str, Any]) -> bytes:
    """Devuelve el workbook F10-03 como bytes para descarga."""
    wb = build_f10_03_workbook(solicitud)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
