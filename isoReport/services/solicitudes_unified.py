"""
Unión F10-01 (Excel) + JSON (paso_1/paso_2) → lista de Solicitud unificada.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from models.solicitud import Solicitud, from_paso1_paso2_f10_01_row
from utils.normalizers import numero_solicitud_canonico
from utils.solicitud_data import raw_to_solicitudes


# Nombres de columna esperados en F10-01 (primera fila = cabecera)
F10_01_COL_NUMERO = "Nº Solicitud"
F10_01_COLUMNS = [
    "Nº Solicitud",
    "Solicitante",
    "Nombre proyecto",
    "Necesidad",
    "Producto competencia",
    "Volumen competencia",
    "Precio competencia",
    "Volumen propuesto",
    "Envase",
    "País destino",
    "Aceptado",
    "Finalizado",
    "Motivo denegado",
    "Fecha aprobación solicitud",
    "Tiempo estimado (días laborables)",
    "Fecha finalización estimada",
    "Fecha finalización real",
    "Horas empleadas I+D",
    "Horas empleadas Calidad",
    "Problemas",
    "Comentarios",
]


def _get_available_columns(df: pd.DataFrame) -> List[str]:
    """Devuelve las columnas de df que existen (para no asumir todas)."""
    return [c for c in F10_01_COLUMNS if c in df.columns]


def _canon_from_f10_01_row(row: pd.Series, col_numero: str) -> str:
    """Extrae numero_solicitud_canonico de una fila del Excel F10-01."""
    val = row.get(col_numero) if hasattr(row, "get") else getattr(row, col_numero, None)
    return numero_solicitud_canonico(val)


def build_unified_list(
    df_f10_01: pd.DataFrame,
    raw_json: Dict[str, Any],
    year: int,
) -> List[Solicitud]:
    """
    Construye la lista unificada de solicitudes para el año dado.
    - Incluye filas de F10-01: si hay match en JSON (por numero_solicitud_canonico + producto_base_linea), origen f10_01_y_json; si no, solo_f10_01 (paso_1/paso_2 vacíos).
    - Incluye solicitudes que solo están en JSON (sin fila en F10-01 para este año): origen solo_json, f10_01_row=None.
    """
    solicitudes_raw = raw_to_solicitudes(raw_json)
    # Índice (num_canon, producto) -> (paso_1, paso_2)
    json_by_key: Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for s in solicitudes_raw:
        p1 = s["paso_1"]
        p2 = s["paso_2"]
        num = numero_solicitud_canonico(p1.get("numero_solicitud"))
        prod = (str(p1.get("producto_base_linea") or "").strip())[:80]
        json_by_key[(num, prod)] = (p1, p2)

    result: List[Solicitud] = []
    seen_json_keys: set[Tuple[str, str]] = set()

    # 1) Recorrer filas F10-01
    cols = _get_available_columns(df_f10_01)
    col_numero = F10_01_COL_NUMERO if F10_01_COL_NUMERO in df_f10_01.columns else (df_f10_01.columns[0] if len(df_f10_01.columns) > 0 else None)

    if col_numero and not df_f10_01.empty:
        for idx in df_f10_01.index:
            row = df_f10_01.loc[idx]
            num_canon = _canon_from_f10_01_row(row, col_numero)
            if not num_canon:
                continue
            # Buscar match en JSON por numero (producto puede venir de "Nombre proyecto")
            nombre_proyecto = ""
            if "Nombre proyecto" in df_f10_01.columns:
                v = row.get("Nombre proyecto") if hasattr(row, "get") else getattr(row, "Nombre proyecto", None)
                nombre_proyecto = (str(v).strip() if v is not None else "")[:80]
            p1_match: Optional[Dict[str, Any]] = None
            p2_match: Optional[Dict[str, Any]] = None
            key_match: Optional[Tuple[str, str]] = None
            for (n, prod), (p1, p2) in json_by_key.items():
                if n == num_canon:
                    p1_match, p2_match = p1, p2
                    key_match = (n, prod)
                    if nombre_proyecto and prod == nombre_proyecto:
                        break
            if p1_match is not None and p2_match is not None and key_match:
                seen_json_keys.add(key_match)
                result.append(
                    from_paso1_paso2_f10_01_row(
                        p1_match,
                        p2_match,
                        year,
                        f10_01_row=row,
                        f10_01_columns=cols or list(df_f10_01.columns),
                    )
                )
            else:
                # Solo F10-01: paso_1 y paso_2 mínimos vacíos
                paso_1_min = {
                    "numero_solicitud": int(num_canon) if num_canon.isdigit() else num_canon,
                    "producto_base_linea": nombre_proyecto,
                    "responsable": "",
                    "tipo": "",
                    "descripcion_partida_diseno": "",
                    "verificacion_diseno": {"producto_final": "", "formula_ok": "", "riquezas": ""},
                }
                paso_2_min = {
                    "numero_solicitud": num_canon,
                    "producto_base_linea": nombre_proyecto,
                    "clave_incidencia_jira": "",
                    "ensayos": [],
                }
                sol = from_paso1_paso2_f10_01_row(
                    paso_1_min,
                    paso_2_min,
                    year,
                    f10_01_row=row,
                    f10_01_columns=cols or list(df_f10_01.columns),
                )
                sol.origen = "solo_f10_01"
                sol.paso_1 = paso_1_min
                sol.paso_2 = paso_2_min
                result.append(sol)

    # 2) Añadir solicitudes que solo están en JSON (no aparecieron en F10-01 para este año)
    for (n, prod), (p1, p2) in json_by_key.items():
        if (n, prod) in seen_json_keys:
            continue
        result.append(
            from_paso1_paso2_f10_01_row(p1, p2, year, f10_01_row=None, f10_01_columns=None)
        )

    return result


def _is_initialized_in_json(s: Solicitud) -> bool:
    """True si la solicitud tiene datos reales (vino de JSON o ya se inicializó en bbdd)."""
    if s.origen == "solo_json" or s.origen == "f10_01_y_json":
        return True
    if s.origen == "solo_f10_01":
        p1 = s.paso_1 or {}
        v = p1.get("verificacion_diseno") or {}
        return bool(
            (p1.get("responsable") or "").strip()
            or (p1.get("descripcion_partida_diseno") or "").strip()
            or (v.get("producto_final") or "").strip()
        )
    return False


def unified_list_to_raw(solicitudes: List[Solicitud]) -> Dict[str, Any]:
    """
    Convierte la lista unificada de vuelta a {"paso_1": [...], "paso_2": [...]}.
    Incluye solo solicitudes que tienen datos en JSON (o ya inicializadas en bbdd).
    Excluye solo_f10_01 que aún no se han inicializado.
    """
    from utils.solicitud_data import solicitudes_to_raw

    list_dicts: List[Dict[str, Any]] = []
    for s in solicitudes:
        if not _is_initialized_in_json(s):
            continue
        list_dicts.append({"paso_1": dict(s.paso_1), "paso_2": dict(s.paso_2)})
    return solicitudes_to_raw(list_dicts)
