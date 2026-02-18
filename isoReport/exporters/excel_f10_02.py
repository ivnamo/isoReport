"""
Exportación F10-02 (Diseño producto): workbook generado por código (modo provisional).
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from models.solicitud import Solicitud


def build_f10_02_workbook(solicitud: Solicitud) -> Workbook:
    """Construye un workbook con la estructura F10-02 rellenada desde la solicitud."""
    wb = Workbook()
    ws = wb.active
    ws.title = "F10-02 Diseño producto"
    p1 = solicitud.paso_1 or {}
    p2 = solicitud.paso_2 or {}
    v = p1.get("verificacion_diseno") or {}
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

    ws.cell(row, 1, "1. DATOS DE PARTIDA DEL DISEÑO")
    row += 1
    ws.cell(row, 1, p1.get("descripcion_partida_diseno", ""))
    row += 2

    ws.cell(row, 1, "2. ENSAYOS / FORMULACIÓN")
    row += 2
    ensayos = p2.get("ensayos") or []
    for idx, ens in enumerate(ensayos, start=1):
        row = _write_ensayo_block(ws, ens, idx, row)
        row += 2

    ws.cell(row, 1, "3. VERIFICACIÓN (DISEÑO)")
    row += 1
    ws.cell(row, 1, "Producto final:")
    ws.cell(row, 2, v.get("producto_final", ""))
    row += 1
    ws.cell(row, 1, "Fórmula OK:")
    ws.cell(row, 2, v.get("formula_ok", ""))
    row += 1
    ws.cell(row, 1, "Riquezas:")
    ws.cell(row, 2, v.get("riquezas", ""))
    row += 1

    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = 25
    return wb


def _write_ensayo_block(ws: Worksheet, ens: Dict[str, Any], idx: int, start_row: int) -> int:
    row = start_row
    ws.cell(row, 1, f"Ensayo {idx}")
    ws.cell(row, 2, str(ens.get("id", "")))
    ws.cell(row, 3, str(ens.get("ensayo", "")))
    row += 1
    ws.cell(row, 1, "Fecha:")
    ws.cell(row, 2, str(ens.get("fecha", "")))
    ws.cell(row, 3, "Resultado:")
    ws.cell(row, 4, str(ens.get("resultado", "")))
    row += 1
    formula = ens.get("formula") or []
    ws.cell(row, 1, "Materia prima")
    ws.cell(row, 2, "% peso")
    row += 1
    for item in formula:
        ws.cell(row, 1, str(item.get("materia_prima", "")))
        ws.cell(row, 2, str(item.get("porcentaje_peso", "")))
        row += 1
    row += 1
    ws.cell(row, 1, "Motivo / comentario")
    ws.cell(row, 2, str(ens.get("motivo_comentario", "")))
    row += 1
    return row


def build_f10_02_bytes(solicitud: Solicitud) -> bytes:
    """Devuelve el workbook F10-02 como bytes para descarga."""
    wb = build_f10_02_workbook(solicitud)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
