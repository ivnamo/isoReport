"""
Carga y guardado del JSON con estructura { "solicitudes": [...] } y guardado atómico.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_raw(path: str | Path) -> Dict[str, Any]:
    """
    Carga el JSON desde disco.
    Devuelve {"solicitudes": []}. Si el fichero no existe o está vacío, devuelve estructura vacía.
    Si el archivo tiene formato antiguo (paso_1/paso_2), devuelve {"solicitudes": []} para no romper la app
    (ejecutar antes el script de migración).
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return {"solicitudes": []}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("El JSON debe ser un objeto con clave solicitudes")
    if "solicitudes" not in raw:
        if "paso_1" in raw or "paso_2" in raw:
            return {"solicitudes": []}
        raw["solicitudes"] = []
    if not isinstance(raw["solicitudes"], list):
        raise ValueError("solicitudes debe ser una lista")
    return raw


def save_raw(path: str | Path, raw: Dict[str, Any]) -> None:
    """
    Guarda el JSON en disco con guardado atómico (escribir a .tmp y renombrar).
    raw debe ser {"solicitudes": [...]}.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if "solicitudes" not in raw or not isinstance(raw.get("solicitudes"), list):
        raise ValueError("raw debe contener solicitudes como lista")
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)
