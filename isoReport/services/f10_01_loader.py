"""
Carga del Excel F10-01 por hoja (año). Primera fila = cabecera.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

import pandas as pd
import streamlit as st


def get_available_years(path: Union[str, Path]) -> List[int]:
    """Devuelve los nombres de hoja que son años (enteros) del Excel F10-01."""
    path = Path(path)
    if not path.exists():
        return [2025]
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
        years = []
        for name in xl.sheet_names:
            try:
                y = int(name.strip())
                if 2000 <= y <= 2100:
                    years.append(y)
            except ValueError:
                pass
        return sorted(years, reverse=True) if years else [2025]
    except Exception:
        return [2025]


@st.cache_data(ttl=300)
def load_f10_01_sheet(path: Union[str, Path], year: int) -> pd.DataFrame:
    """
    Carga la hoja del Excel F10-01 correspondiente al año.
    Hoja = str(year) (ej. "2025"). Primera fila = cabecera.
    Si la hoja no existe, devuelve DataFrame vacío.
    """
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(path, sheet_name=str(year), engine="openpyxl")
    except ValueError:
        return pd.DataFrame()
    if df.empty:
        return df
    df.columns = [str(c).strip() for c in df.columns]
    return df
