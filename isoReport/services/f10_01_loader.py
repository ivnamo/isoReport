"""
Carga del F10-01 desde CSV por año (primera fila = cabecera, columna ID única).
Soporta también Excel por compatibilidad si se pasa un .xlsx.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Union

import pandas as pd
import streamlit as st

import config


def get_available_years(path: Union[str, Path, None] = None) -> List[int]:
    """
    Devuelve años disponibles: si path es un directorio o None, busca CSV F10-01*__<año>.csv;
    si es un .xlsx, usa hojas del Excel (compatibilidad).
    """
    if path is None:
        path = config.DEFAULT_F10_01_DIR
    path = Path(path)
    if not path.exists():
        return [2025]
    years: List[int] = []
    if path.is_dir():
        for f in path.glob(config.F10_01_CSV_PATTERN):
            # Ej: F10-01 Viabilidad y planificación de diseños__2025.csv -> 2025
            m = re.search(r"__(\d{4})\.csv$", f.name, re.IGNORECASE)
            if m:
                try:
                    y = int(m.group(1))
                    if 2000 <= y <= 2100:
                        years.append(y)
                except ValueError:
                    pass
        return sorted(set(years), reverse=True) if years else [2025]
    # Archivo: .csv único (año del nombre o 2025 por defecto)
    if path.suffix.lower() == ".csv":
        m = re.search(r"__(\d{4})\.csv$", path.name, re.IGNORECASE)
        return [int(m.group(1))] if m and 2000 <= int(m.group(1)) <= 2100 else [2025]
    # Excel (compatibilidad)
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
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


def _path_for_year(year: int) -> Path:
    """Ruta al CSV F10-01 para el año dado (primer archivo que coincida __<year>.csv)."""
    d = config.DEFAULT_F10_01_DIR
    for f in d.glob(config.F10_01_CSV_PATTERN):
        if f.name.endswith(f"__{year}.csv"):
            return f
    return d / f"F10-01 Viabilidad y planificación de diseños__{year}.csv"


@st.cache_data(ttl=300)
def load_f10_01_sheet(path: Union[str, Path], year: int) -> pd.DataFrame:
    """
    Carga el F10-01 para el año: CSV (con columna ID) o Excel por hoja.
    Si path es directorio, se busca el CSV con __<year>.csv.
    """
    path = Path(path)
    if path.is_dir():
        path = _path_for_year(year)
    if not path.exists():
        return pd.DataFrame()
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(path, encoding="utf-8")
        else:
            df = pd.read_excel(path, sheet_name=str(year), engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    df.columns = [str(c).strip() for c in df.columns]
    return df
