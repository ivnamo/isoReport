"""
Modelo Solicitud: vista en memoria a partir de un elemento de solicitudes[] (id, numero_solicitud, f10_01, f10_02, f10_03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from utils.normalizers import numero_solicitud_canonico


@dataclass
class Solicitud:
    """Una solicitud: id, numero_solicitud, f10_01 (datos CSV), f10_02 (diseño), f10_03 (validación)."""

    id: int | None
    numero_solicitud: str
    f10_01: Dict[str, Any]
    f10_02: Dict[str, Any]
    f10_03: Dict[str, Any]

    @property
    def numero_solicitud_canonico(self) -> str:
        """Número canónico para ordenación y comparación (parte izquierda de 'x/2025')."""
        return numero_solicitud_canonico(self.numero_solicitud)

    @property
    def year(self) -> int:
        """Año extraído de numero_solicitud (ej. '2/2025' -> 2025)."""
        s = (self.numero_solicitud or "").strip()
        if "/" in s:
            part = s.split("/", 1)[1].strip()
            try:
                return int(part)
            except ValueError:
                pass
        return 2025

    @property
    def f10_01_id(self) -> int | None:
        """ID único de la solicitud (alias de id)."""
        return self.id

    @property
    def f10_01_row(self) -> Dict[str, Any]:
        """Alias para compatibilidad UI: datos F10-01 como dict (mismas claves que CSV)."""
        return self.f10_01

    def has_json_data(self) -> bool:
        """True si tiene f10_02/f10_03 con contenido editable (responsable, descripción, ensayos, etc.)."""
        f02 = self.f10_02 or {}
        f03 = self.f10_03 or {}
        return bool(
            (f02.get("responsable") or "").strip()
            or (f02.get("descripcion_partida_diseno") or "").strip()
            or (f02.get("ensayos") or [])
            or (f03.get("especificacion_final") or {}).get("descripcion")
            or (f03.get("validacion") or {}).get("filas")
        )

    def _is_externa(self) -> bool:
        """True si SOLICITANTE indica externo (muestra 01/2025)."""
        sol = (self.f10_01 or {}).get("SOLICITANTE") or ""
        return "extern" in str(sol).strip().lower()

    @property
    def display_numero(self) -> str:
        """Número de solicitud para mostrar en UI (01/2025 para externas, 1/2025 para internas)."""
        num = self.numero_solicitud_canonico
        y = self.year
        if self._is_externa():
            return f"{num.zfill(2)}/{y}"
        return f"{num}/{y}" if "/" not in (self.numero_solicitud or "") else (self.numero_solicitud or num)

    # Compatibilidad: paso_1 / paso_2 como propiedades derivadas para no romper referencias en UI hasta que las sustituyamos
    @property
    def paso_1(self) -> Dict[str, Any]:
        """Vista paso_1 desde f10_02 + cabecera (para transición UI)."""
        f01 = self.f10_01 or {}
        f02 = self.f10_02 or {}
        v = f02.get("verificacion_diseno") or {}
        return {
            "numero_solicitud": self.numero_solicitud,
            "producto_base_linea": (f01.get("NOMBRE") or f01.get("NOM_COMERCIAL") or "").strip(),
            "responsable": f02.get("responsable", ""),
            "descripcion_partida_diseno": f02.get("descripcion_partida_diseno", ""),
            "verificacion_diseno": {
                "producto_final": v.get("producto_final", ""),
                "formula_ok": v.get("formula_ok", ""),
                "riquezas": v.get("riquezas", ""),
            },
            "anexo_f10_03": self.f10_03,
        }

    @paso_1.setter
    def paso_1(self, value: Dict[str, Any]) -> None:
        """Escribir en f10_02 y f10_03 desde paso_1 (transición)."""
        if not value:
            return
        self.f10_02 = self.f10_02 or {}
        self.f10_02["responsable"] = value.get("responsable", "")
        self.f10_02["descripcion_partida_diseno"] = value.get("descripcion_partida_diseno", "")
        self.f10_02["verificacion_diseno"] = value.get("verificacion_diseno") or {}
        if "anexo_f10_03" in value and value["anexo_f10_03"]:
            self.f10_03 = value["anexo_f10_03"]

    @property
    def paso_2(self) -> Dict[str, Any]:
        """Vista paso_2 desde f10_02.ensayos (para transición UI)."""
        f02 = self.f10_02 or {}
        return {"ensayos": list(f02.get("ensayos") or [])}

    @paso_2.setter
    def paso_2(self, value: Dict[str, Any]) -> None:
        """Escribir ensayos en f10_02."""
        self.f10_02 = self.f10_02 or {}
        self.f10_02["ensayos"] = list(value.get("ensayos") or [])


def from_solicitud_dict(item: Dict[str, Any]) -> Solicitud:
    """Construye una Solicitud desde un elemento de solicitudes[]."""
    return Solicitud(
        id=item.get("id"),
        numero_solicitud=str(item.get("numero_solicitud") or "").strip(),
        f10_01=dict(item.get("f10_01") or {}),
        f10_02=dict(item.get("f10_02") or {}),
        f10_03=dict(item.get("f10_03") or {}),
    )


def solicitud_to_dict(solicitud: Solicitud) -> Dict[str, Any]:
    """Serializa una Solicitud a elemento de solicitudes[] (id, numero_solicitud, f10_01, f10_02, f10_03)."""
    return {
        "id": solicitud.id,
        "numero_solicitud": solicitud.numero_solicitud,
        "f10_01": dict(solicitud.f10_01),
        "f10_02": dict(solicitud.f10_02),
        "f10_03": dict(solicitud.f10_03),
    }
