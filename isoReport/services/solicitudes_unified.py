"""
Lista de solicitudes desde JSON { "solicitudes": [...] }. Orden por numero_solicitud.
Sin unión con CSV: F10-01 está dentro de cada solicitud en f10_01.
"""

from __future__ import annotations

from typing import Any, Dict, List

from models.solicitud import Solicitud, from_solicitud_dict, solicitud_to_dict


def _sort_key(s: Solicitud) -> tuple:
    """Ordenar por número de solicitud (parte numérica) y luego por id."""
    try:
        num = int(s.numero_solicitud_canonico or "0")
    except ValueError:
        num = 0
    return (num, s.id or 0)


def build_unified_list(raw: Dict[str, Any]) -> List[Solicitud]:
    """
    Construye la lista de solicitudes desde raw["solicitudes"].
    Orden ascendente por numero_solicitud (parte numérica).
    """
    items = raw.get("solicitudes") or []
    result = [from_solicitud_dict(x) for x in items if isinstance(x, dict)]
    result.sort(key=_sort_key)
    return result


def unified_list_to_raw(solicitudes: List[Solicitud]) -> Dict[str, Any]:
    """Convierte la lista de Solicitud a { "solicitudes": [...] }."""
    return {"solicitudes": [solicitud_to_dict(s) for s in solicitudes]}
