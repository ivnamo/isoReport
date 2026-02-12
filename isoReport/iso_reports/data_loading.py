"""
Carga de archivos para Paso 1: listado Jira ISO y BBDD_Sesion-PT-INAVARRO.

Acepta CSV (cualquier delimitador) y Excel (.xlsx, .xls).
"""

from __future__ import annotations

import csv
import io
from typing import Union

import pandas as pd


def _detect_delimiter(sample: bytes) -> str:
    """Detecta el delimitador de un CSV a partir de una muestra."""
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample.decode("utf-8", errors="ignore"))
        return dialect.delimiter
    except Exception:
        return ";"


def _read_csv(file_obj) -> pd.DataFrame:
    """Lee un CSV (delimitador auto-detectado). Acepta UploadedFile o ruta."""
    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        buffer = io.BytesIO(raw)
        sample = raw[:2048]
    else:
        with open(file_obj, "rb") as fh:
            raw = fh.read()
        buffer = io.BytesIO(raw)
        sample = raw[:2048]

    delimiter = _detect_delimiter(sample)
    buffer.seek(0)
    df = pd.read_csv(buffer, sep=delimiter, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _read_excel(file_obj, sheet_name: Union[str, int] = 0) -> pd.DataFrame:
    """Lee la primera hoja de un Excel."""
    df = pd.read_excel(file_obj, sheet_name=sheet_name, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_table(file_obj) -> pd.DataFrame:
    """
    Carga una tabla desde CSV o Excel (listado Jira o BBDD).
    - CSV: .csv (delimitador auto)
    - Excel: .xlsx, .xls
    """
    name = getattr(file_obj, "name", "").lower()
    if name.endswith((".xlsx", ".xls")):
        return _read_excel(file_obj)
    return _read_csv(file_obj)
