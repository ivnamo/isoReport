from __future__ import annotations

from typing import List

from .models import Ensayo, InformeData, MateriaPrima


def _safe_cell(value) -> str:
    if value is None:
        return ""
    t = str(value).replace("\r", " ").replace("\n", " ").strip()
    return t


def _csv_escape(cell: str) -> str:
    """
    Aplica reglas mínimas de escapado para construir un CSV con ';'
    compatible con tu flujo actual.
    """
    t = _safe_cell(cell)
    if '"' in t:
        t = t.replace('"', '""')
    if any(ch in t for ch in [";", '"']):
        t = f'"{t}"'
    return t


def build_informe_iso_csv(informe: InformeData) -> bytes:
    """
    Genera un CSV “maquetado” tipo informe ISO a partir de un InformeData,
    manteniendo el layout básico del script original:

    1. Datos de partida
    2. Ensayos / formulaciones
    3. Verificación
    """
    rows: List[List[str]] = []

    # --- Cabecera ---
    rows.append(["Responsable de proyecto:", informe.responsable])
    rows.append(
        [
            "Nº Solicitud:",
            informe.numero_solicitud,
            "Tipo:",
            informe.tipo_solicitud,
        ]
    )
    rows.append(["Producto base / línea:", informe.producto_base])
    rows.append([])

    # --- 1. Datos de partida ---
    rows.append(["1. DATOS DE PARTIDA DEL DISEÑO"])
    rows.append([informe.descripcion_diseno])
    rows.append([])

    # --- 2. Ensayos / formulaciones ---
    rows.append(["2. ENSAYOS / FORMULACIONES"])
    rows.append([])

    for idx, ensayo in enumerate(informe.ensayos, start=1):
        _add_ensayo_block(rows, ensayo, idx)

    # --- 3. Verificación ---
    rows.append(["3. VERIFICACIÓN"])
    rows.append(["Producto final:", informe.producto_final])
    rows.append(["Fórmula OK:", informe.formula_ok])
    rows.append(["Riquezas:", informe.riquezas])
    rows.append([])

    # --- ANEXO F90-02 (resumen, no maquetado al detalle) ---
    espec = informe.especificacion_final
    valid = informe.validacion_producto

    rows.append(["ANEXO F90-02: VALIDACIÓN DE PRODUCTO"])
    rows.append(["1. ESPECIFICACIÓN FINAL"])
    rows.append(["DESCRIPCIÓN:", espec.descripcion])
    rows.append(["CARACTERÍSTICAS FÍSICAS"])
    rows.append(["Aspecto:", espec.aspecto])
    rows.append(["Densidad:", espec.densidad])
    rows.append(["Color:", espec.color])
    rows.append(["pH:", espec.ph])
    rows.append(["CARACTERÍSTICAS QUÍMICAS"])
    rows.append([espec.caracteristicas_quimicas])
    rows.append([])
    rows.append(["2. VALIDACIÓN (El producto satisface los requisitos)"])
    rows.append(["Fecha de validación:", valid.fecha_validacion])
    rows.append(["Comentario validación:", valid.comentario_validacion])
    rows.append([])

    # Convertir a texto CSV con separador ';' y BOM UTF‑8
    out_lines: List[str] = []
    for cols in rows:
        out_cells = [_csv_escape(c) for c in cols]
        out_lines.append(";".join(out_cells))

    csv_content = "\r\n".join(out_lines)
    return ("\ufeff" + csv_content).encode("utf-8")


def _add_ensayo_block(rows: List[List[str]], ensayo: Ensayo, idx: int) -> None:
    """
    Añade al listado de filas el bloque para un ensayo concreto.
    """
    header = f"Ensayo {idx}"
    rows.append([header, ensayo.id_ensayo, ensayo.nombre_formulacion])

    # Línea con fecha / resultado (y opcionalmente Jira)
    linea_fecha = [
        "Fecha ensayo:",
        ensayo.fecha_ensayo,
        "Resultado:",
        ensayo.resultado,
    ]
    if ensayo.jira_estado or ensayo.jira_persona_asignada:
        linea_fecha.extend(
            [
                "Estado Jira:",
                ensayo.jira_estado or "",
                "Asignado:",
                ensayo.jira_persona_asignada or "",
            ]
        )
    rows.append(linea_fecha)
    rows.append([])

    # Tabla de receta
    rows.append(["Materia prima", "% peso"])
    for mp in ensayo.materias:
        rows.append([mp.nombre, mp.porcentaje_peso])

    rows.append([])

    # Motivo / comentario
    texto_motivo = ensayo.motivo
    if ensayo.jira_resumen:
        texto_motivo = f"{texto_motivo}\n\n[Resumen Jira] {ensayo.jira_resumen}".strip()
    if ensayo.jira_comentarios_resumen:
        texto_motivo = f"{texto_motivo}\n\n[Comentarios Jira]\n{ensayo.jira_comentarios_resumen}".strip()

    rows.append(["Motivo / comentario:", texto_motivo])
    rows.append([])
    rows.append([])


