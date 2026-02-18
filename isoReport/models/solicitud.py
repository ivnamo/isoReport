"""
Modelo Solicitud unificada (vista en memoria) y mapeo bidireccional con paso_1/paso_2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from utils.normalizers import numero_solicitud_canonico
from utils.solicitud_data import ensure_anexo_f10_03


@dataclass
class Solicitud:
    """Vista unificada de una solicitud (F10-01 + JSON)."""

    numero_solicitud_canonico: str
    year: int
    origen: Literal["f10_01_y_json", "solo_f10_01", "solo_json"]
    f10_01_row: Optional[Dict[str, Any]] = None
    paso_1: Dict[str, Any] = field(default_factory=dict)
    paso_2: Dict[str, Any] = field(default_factory=dict)

    def has_json_data(self) -> bool:
        """True si tiene paso_1/paso_2 con contenido (puede editar F10-02/F10-03)."""
        return bool(self.paso_1 or self.paso_2)


def _row_to_dict(row: Any, columns: List[str]) -> Dict[str, Any]:
    """Convierte una fila (Series o dict) a dict con las columnas dadas."""
    out: Dict[str, Any] = {}
    for col in columns:
        if hasattr(row, "get"):
            val = row.get(col)
        else:
            val = getattr(row, col, None)
        if hasattr(val, "item"):  # numpy scalar
            try:
                val = val.item()
            except (ValueError, AttributeError):
                pass
        out[col] = val
    return out


def from_paso1_paso2_f10_01_row(
    paso_1: Dict[str, Any],
    paso_2: Dict[str, Any],
    year: int,
    f10_01_row: Optional[Any] = None,
    f10_01_columns: Optional[List[str]] = None,
) -> Solicitud:
    """
    Construye una Solicitud desde paso_1, paso_2 y opcionalmente una fila F10-01.
    numero_solicitud_canonico desde paso_1.numero_solicitud; origen según si hay f10_01_row.
    """
    num_canon = numero_solicitud_canonico(paso_1.get("numero_solicitud"))
    if f10_01_row is not None and f10_01_columns:
        f10_dict = _row_to_dict(f10_01_row, f10_01_columns)
        origen: Literal["f10_01_y_json", "solo_f10_01", "solo_json"] = "f10_01_y_json"
    else:
        f10_dict = None
        origen = "solo_json"
    return Solicitud(
        numero_solicitud_canonico=num_canon,
        year=year,
        origen=origen,
        f10_01_row=f10_dict,
        paso_1=paso_1,
        paso_2=paso_2,
    )


def solicitud_to_paso1_paso2(solicitud: Solicitud) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Devuelve (paso_1, paso_2) para persistir en JSON. No modifica solicitud."""
    return (dict(solicitud.paso_1), dict(solicitud.paso_2))
