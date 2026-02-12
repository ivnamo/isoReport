from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MateriaPrima:
    """Una línea de receta: materia prima + porcentaje en peso."""

    nombre: str
    porcentaje_peso: str  # se mantiene como texto para respetar el original


@dataclass
class Ensayo:
    """
    Representa un bloque de ensayo/formulación dentro del informe.
    Origen: BBDD F10-02 + enriquecimiento con Jira.
    """

    id_ensayo: str
    nombre_formulacion: str
    fecha_ensayo: str
    resultado: str
    motivo: str
    materias: List[MateriaPrima] = field(default_factory=list)

    # Metadatos Jira opcionales
    jira_tipo_incidencia: Optional[str] = None
    jira_clave: Optional[str] = None
    jira_id: Optional[str] = None
    jira_resumen: Optional[str] = None
    jira_proyecto_id: Optional[str] = None
    jira_persona_asignada: Optional[str] = None
    jira_estado: Optional[str] = None
    jira_fecha_creada: Optional[str] = None
    jira_fecha_vencimiento: Optional[str] = None
    jira_fecha_actualizada: Optional[str] = None
    jira_fecha_resuelta: Optional[str] = None
    jira_descripcion: Optional[str] = None
    jira_comentarios_resumen: Optional[str] = None
    jira_prioridad: Optional[str] = None
    jira_etiquetas: Optional[str] = None


@dataclass
class EspecificacionFinal:
    """Datos del bloque de especificación del ANEXO F90-02."""

    descripcion: str = ""
    aspecto: str = ""
    densidad: str = ""
    color: str = ""
    ph: str = ""
    caracteristicas_quimicas: str = ""


@dataclass
class ValidacionProducto:
    """Datos del bloque de validación del producto en el ANEXO."""

    fecha_validacion: str = ""
    comentario_validacion: str = ""


@dataclass
class InformeData:
    """
    Agrega toda la información necesaria para construir un
    informe ISO completo para un Nº de Solicitud.
    """

    # Meta / cabecera (fuente principal: Solicitudes 2025)
    responsable: str
    numero_solicitud: str
    tipo_solicitud: str
    producto_base: str
    descripcion_diseno: str

    # Sección 2 – ensayos/formulaciones
    ensayos: List[Ensayo] = field(default_factory=list)

    # Sección 3 – verificación (mezcla de Solicitudes + Jira LIBERADA)
    producto_final: str = ""
    formula_ok: str = ""
    riquezas: str = ""

    # Datos adicionales sin ubicación fija en el layout
    extra_meta: Dict[str, Any] = field(default_factory=dict)

    # ANEXO F90-02
    especificacion_final: EspecificacionFinal = field(
        default_factory=EspecificacionFinal
    )
    validacion_producto: ValidacionProducto = field(
        default_factory=ValidacionProducto
    )


__all__ = [
    "MateriaPrima",
    "Ensayo",
    "EspecificacionFinal",
    "ValidacionProducto",
    "InformeData",
]

