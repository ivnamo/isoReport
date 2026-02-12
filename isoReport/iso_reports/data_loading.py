from __future__ import annotations

import csv
import io
from typing import Optional

import pandas as pd


def _detect_delimiter(sample: bytes) -> str:
    """Intenta detectar el delimitador de un CSV a partir de una muestra."""
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample.decode("utf-8", errors="ignore"))
        return dialect.delimiter
    except Exception:
        return ";"  # valor por defecto razonable


def read_csv_flexible(file_obj) -> pd.DataFrame:
    """
    Lee un CSV tolerante a delimitadores desconocidos.
    Acepta tanto UploadedFile de Streamlit como rutas locales.
    """
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
    df = pd.read_csv(buffer, sep=delimiter, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_solicitudes_excel(file_obj, sheet_name: Optional[str | int] = 0) -> pd.DataFrame:
    """
    Carga el Excel de Solicitudes 2025.

    No fuerza nombres de columnas concretos: simplemente limpia espacios.
    """
    df = pd.read_excel(file_obj, sheet_name=sheet_name, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_bbdd_csv(file_obj) -> pd.DataFrame:
    """
    Carga una BBDD F10-02 exportada (CSV).
    Mantiene las columnas existentes y no aplica lógica adicional.
    """
    return read_csv_flexible(file_obj)


def load_jira_export(file_obj) -> pd.DataFrame:
    """
    Carga la exportación de Jira (normalmente CSV).
    """
    # Permitimos también Excel, por si en el futuro lo usas así.
    name = getattr(file_obj, "name", "")
    if name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_obj, sheet_name=0, engine="openpyxl")
    else:
        df = read_csv_flexible(file_obj)

    df.columns = [str(c).strip() for c in df.columns]
    return df


