"""
Carga y guardado del JSON (paso_1, paso_2) con guardado atómico.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def load_raw(path: str | Path) -> Dict[str, Any]:
    """
    Carga el JSON desde disco.
    Devuelve {"paso_1": [], "paso_2": []} o lanza si el formato es inválido.
    Si el fichero no existe o está vacío, devuelve estructura vacía.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return {"paso_1": [], "paso_2": []}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("El JSON debe ser un objeto con paso_1 y paso_2")
    if "paso_1" not in raw:
        raw["paso_1"] = []
    if "paso_2" not in raw:
        raw["paso_2"] = []
    if not isinstance(raw["paso_1"], list) or not isinstance(raw["paso_2"], list):
        raise ValueError("paso_1 y paso_2 deben ser listas")
    return raw


def save_raw(path: str | Path, raw: Dict[str, Any]) -> None:
    """
    Guarda el JSON en disco con guardado atómico (escribir a .tmp y renombrar).
    Crea el directorio padre si no existe.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(raw.get("paso_1"), list) or not isinstance(raw.get("paso_2"), list):
        raise ValueError("raw debe contener paso_1 y paso_2 como listas")
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)
