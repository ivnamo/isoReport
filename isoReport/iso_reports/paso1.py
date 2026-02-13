"""
Paso 1: cabecera / datos generales.

Genera un Paso 1 por cada Nº Solicitud único en la BBDD (una solicitud por proyecto),
enlazando con Jira por ProyectoID == Producto base para ensayos.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pandas as pd


# Alias por si el export tiene otro nombre para ProyectoID
JIRA_PROYECTO_ALIAS = ["ProyectoID", "Campo personalizado (ProyectoID)"]

BBDD_COLUMN_DESCRIPCION = "Descripción diseño"
BBDD_COLUMN_ID_ENSAYO = "ID ensayo"
BBDD_COLUMN_NUMERO_SOLICITUD = "Nº Solicitud"
BBDD_COLUMN_PRODUCTO_BASE = "Producto base"
BBDD_COLUMN_RESPONSABLE = "Responsable"
BBDD_COLUMN_TIPO = "Tipo"
BBDD_COLUMNS_REQUIRED = [BBDD_COLUMN_NUMERO_SOLICITUD, BBDD_COLUMN_PRODUCTO_BASE, BBDD_COLUMN_DESCRIPCION]

# Para el flujo "from_master" no se usa Nº Solicitud; solo estas columnas para cabecera y joins
BBDD_COLUMNS_REQUIRED_FOR_MASTER = [
    BBDD_COLUMN_PRODUCTO_BASE,
    BBDD_COLUMN_DESCRIPCION,
    BBDD_COLUMN_ID_ENSAYO,
]

# Columnas del listado maestro Solicitudes 2025.xlsx
SOLICITUDES2025_COL_NUMERO_ALIAS = ["Nº Solicitud", "Nº solicitud"]
SOLICITUDES2025_COL_NUMERO = "Nº Solicitud"
SOLICITUDES2025_COL_SOLICITANTE = "SOLICITANTE"
SOLICITUDES2025_COL_NOMBRE = "NOMBRE"

# Detecta ID de ensayo en texto (ID-6, ID - 6, Ensayo 6, etc.)
ID_ENSAYO_REGEX = re.compile(
    r"ID\s*-\s*(\d+)|ID-(\d+)|Ensayo\s*(\d+)",
    re.IGNORECASE,
)


class Paso1Error(Exception):
    """Error de validación o construcción del Paso 1."""

    pass


def _normalize_id_for_match(value: str) -> str:
    """
    Normaliza un ID para comparación: devuelve forma canónica "ID-<número>".
    Así "ID-6", "ID - 6", "id-6", "Ensayo 6" coinciden todos.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    if not s:
        return ""
    m = ID_ENSAYO_REGEX.search(s)
    if m:
        num = m.group(1) or m.group(2) or m.group(3)
        return f"ID-{num}"
    # Sin patrón conocido: mayúsculas y espacios unificados
    return " ".join(s.upper().split())


def _find_column(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    """Devuelve la primera columna que exista en df con alguno de los nombres."""
    for name in names:
        if name in df.columns:
            return name
    return None


def _validate_jira_columns(df: pd.DataFrame) -> None:
    """Comprueba que el listado Jira tenga las columnas requeridas. Lanza Paso1Error si falta alguna."""
    missing = []
    # Persona asignada
    if "Persona asignada" not in df.columns:
        missing.append("Persona asignada")
    # ProyectoID (o alias)
    if _find_column(df, JIRA_PROYECTO_ALIAS) is None:
        missing.append("ProyectoID (o 'Campo personalizado (ProyectoID)')")
    # Clave de incidencia
    if "Clave de incidencia" not in df.columns:
        missing.append("Clave de incidencia")

    if missing:
        raise Paso1Error(
            f"En el archivo 'listado jira iso' faltan las siguientes columnas requeridas: {', '.join(missing)}."
        )


def _validate_bbdd_columns(df: pd.DataFrame) -> None:
    """Comprueba que la BBDD tenga las columnas requeridas. Lanza Paso1Error si falta alguna."""
    missing = [c for c in BBDD_COLUMNS_REQUIRED if c not in df.columns]
    if missing:
        raise Paso1Error(
            f"En el archivo 'BBDD_Sesion-PT-INAVARRO' faltan las columnas requeridas: {', '.join(missing)}."
        )


def _validate_bbdd_columns_for_master(df: pd.DataFrame) -> None:
    """
    Valida BBDD para el flujo desde Solicitudes 2025 (build_all_paso1_from_master).
    No exige Nº Solicitud; solo Producto base, Descripción diseño e ID ensayo (joins por Clave=ID y fallback NOMBRE=Producto base).
    """
    missing = [c for c in BBDD_COLUMNS_REQUIRED_FOR_MASTER if c not in df.columns]
    if missing:
        raise Paso1Error(
            f"En el archivo 'BBDD_Sesion-PT-INAVARRO' faltan las columnas requeridas para este flujo: {', '.join(missing)}."
        )


def _get_id_ensayo_from_bbdd_row(row: pd.Series, df: pd.DataFrame) -> str:
    """
    Obtiene el ID de ensayo de una fila de BBDD (valor en bruto para mostrar en mapeo).
    - Si existe columna 'ID ensayo', usa su valor.
    - Si no, busca en el texto de la fila con regex y devuelve el primer match tal cual.
    """
    if BBDD_COLUMN_ID_ENSAYO in df.columns:
        val = row.get(BBDD_COLUMN_ID_ENSAYO)
        if val is not None and str(val).strip() and str(val) != "nan":
            return str(val).strip()

    text_parts = []
    for _, v in row.items():
        if v is not None and isinstance(v, str) and v.strip():
            text_parts.append(v)
        elif v is not None and not isinstance(v, str):
            text_parts.append(str(v))
    full_text = " ".join(text_parts)
    match = ID_ENSAYO_REGEX.search(full_text)
    if match:
        return match.group(0).strip()
    return ""


def _find_bbdd_row_for_clave(df_bbdd: pd.DataFrame, clave_incidencia: str) -> Optional[pd.Series]:
    """
    Busca en la BBDD la primera fila cuyo ID de ensayo (columna o extraído) coincida
    con clave_incidencia. Comparación con normalización canónica (ID-<n>) para que
    "ID-6" y "ID - 6" coincidan.
    """
    clave_norm = _normalize_id_for_match(clave_incidencia)
    if not clave_norm:
        return None

    seen_canonical: set[str] = set()
    for _, row in df_bbdd.iterrows():
        row_id_raw = _get_id_ensayo_from_bbdd_row(row, df_bbdd)
        if not row_id_raw:
            continue
        row_id_norm = _normalize_id_for_match(row_id_raw)
        if row_id_norm in seen_canonical:
            continue
        seen_canonical.add(row_id_norm)
        if row_id_norm == clave_norm:
            return row
    return None


def _first_jira_row_for_producto(
    df_jira: pd.DataFrame, col_proyecto: Optional[str], producto_base: str
) -> Optional[pd.Series]:
    """Devuelve la primera fila del listado Jira donde ProyectoID == producto_base."""
    if not col_proyecto or not producto_base:
        return None
    producto = str(producto_base).strip()
    if not producto:
        return None
    col_vals = df_jira[col_proyecto].astype(str).str.strip()
    mask = col_vals == producto
    if not mask.any():
        return None
    return df_jira[mask].iloc[0]


def _validate_solicitudes2025_columns(df: pd.DataFrame) -> str:
    """
    Comprueba que el Excel Solicitudes 2025 tenga al menos Nº Solicitud y NOMBRE.
    SOLICITANTE es opcional (si falta, se usará "interno" por defecto).
    Devuelve el nombre de la columna usada para Nº Solicitud. Lanza Paso1Error si falta obligatoria.
    """
    col_num = _find_column(df, SOLICITUDES2025_COL_NUMERO_ALIAS)
    if col_num is None:
        raise Paso1Error(
            "En el archivo 'Solicitudes 2025' falta la columna 'Nº Solicitud' (o 'Nº solicitud')."
        )
    if SOLICITUDES2025_COL_NOMBRE not in df.columns:
        raise Paso1Error(
            "En el archivo 'Solicitudes 2025' falta la columna 'NOMBRE'."
        )
    return col_num


def _sort_key_numero_solicitud(value: Any) -> tuple:
    """Clave de ordenación: numéricos primero (por valor), luego no numéricos (orden estable)."""
    try:
        s = str(value).strip() if value is not None and not (isinstance(value, float) and pd.isna(value)) else ""
        if not s:
            return (float("inf"), "")
        n = int(float(s))
        return (n, s)
    except (ValueError, TypeError):
        return (float("inf"), str(value) if value is not None else "")


def _get_bbdd_rows_by_ensayo_id(df_bbdd: pd.DataFrame, ensayo_id: str) -> pd.DataFrame:
    """Devuelve filas de BBDD donde ID ensayo (normalizado) coincide con ensayo_id (normalizado)."""
    ensayo_norm = _normalize_id_for_match(ensayo_id)
    if not ensayo_norm:
        return df_bbdd.iloc[0:0]
    if BBDD_COLUMN_ID_ENSAYO not in df_bbdd.columns:
        return df_bbdd.iloc[0:0]
    mask = df_bbdd[BBDD_COLUMN_ID_ENSAYO].apply(
        lambda v: _normalize_id_for_match(str(v) if v is not None else "") == ensayo_norm
    )
    return df_bbdd[mask].copy()


def _get_bbdd_representative_row_for_nombre(
    df_bbdd: pd.DataFrame,
    df_jira: pd.DataFrame,
    col_proyecto: Optional[str],
    nombre: str,
) -> Optional[pd.Series]:
    """
    Obtiene una fila representativa de BBDD para rellenar cabecera (descripción, responsable, tipo).
    1) Jira por ProyectoID == nombre; luego BBDD por Clave de incidencia == ID ensayo.
    2) Si no hay match, fallback: BBDD por Producto base == nombre.
    Devuelve la primera fila encontrada o None.
    """
    if not nombre or df_bbdd.empty:
        return None
    nombre = str(nombre).strip()
    # 1) Primera incidencia Jira para este proyecto
    jira_row = _first_jira_row_for_producto(df_jira, col_proyecto, nombre)
    if jira_row is not None:
        clave = str(jira_row.get("Clave de incidencia", "") or "").strip()
        if clave:
            df_match = _get_bbdd_rows_by_ensayo_id(df_bbdd, clave)
            if not df_match.empty:
                return df_match.iloc[0]
    # 2) Fallback: BBDD por Producto base == nombre
    if BBDD_COLUMN_PRODUCTO_BASE not in df_bbdd.columns:
        return None
    col_vals = df_bbdd[BBDD_COLUMN_PRODUCTO_BASE].astype(str).str.strip()
    mask = col_vals == nombre
    if mask.any():
        return df_bbdd[mask].iloc[0]
    return None


def _iter_solicitudes2025_rows(df: pd.DataFrame) -> List[pd.Series]:
    """
    Devuelve la lista de filas del Excel Solicitudes 2025 ordenada:
    numéricos 1..N primero, luego no numéricos (p. ej. "01/2025"), orden estable.
    """
    col_num = _find_column(df, SOLICITUDES2025_COL_NUMERO_ALIAS)
    if col_num is None:
        return []
    df = df.copy()
    df["_sort_key"] = df[col_num].apply(
        lambda v: _sort_key_numero_solicitud(v)
        if pd.notna(v) and str(v).strip() else (float("inf"), "")
    )
    df = df.sort_values(by="_sort_key", kind="stable")
    return [df.loc[i] for i in df.index]


def _unique_numero_solicitud_sorted(series: pd.Series) -> List[Any]:
    """Devuelve valores únicos de Nº Solicitud ordenados (numéricamente si es posible)."""
    uniq = series.dropna().unique().tolist()
    # Intentar orden numérico
    nums: List[Any] = []
    for v in uniq:
        try:
            n = int(float(v)) if v != "" else None
            if n is not None:
                nums.append((n, v))
        except (ValueError, TypeError):
            nums.append((float("inf"), v))  # no numéricos al final
    nums.sort(key=lambda x: (x[0], str(x[1])))
    return [v for _, v in nums]


def build_paso1(
    df_jira: pd.DataFrame,
    df_bbdd: pd.DataFrame,
    *,
    numero_solicitud: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Construye UN solo Paso 1 para el numero_solicitud dado.
    Para generar todas las solicitudes use build_all_paso1.
    """
    all_result = build_all_paso1(df_jira, df_bbdd)
    items = all_result["paso_1"]
    if not items:
        raise Paso1Error("No se generó ninguna solicitud.")
    if numero_solicitud is not None:
        for item in items:
            if item.get("numero_solicitud") == numero_solicitud:
                return {"paso_1": item}
    return {"paso_1": items[0]}


def build_all_paso1(
    df_jira: pd.DataFrame,
    df_bbdd: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Construye un Paso 1 por cada Nº Solicitud único en la BBDD (una solicitud por proyecto).
    - numero_solicitud, producto_base_linea, responsable, descripcion_partida_diseno, tipo: de BBDD.
    - mapeo: clave_incidencia_jira e id_ensayo_detectado desde la primera fila Jira del producto
      (ProyectoID == Producto base), o desde la primera fila BBDD de ese Nº Solicitud si no hay Jira.
    """
    _validate_jira_columns(df_jira)
    _validate_bbdd_columns(df_bbdd)

    if df_bbdd.empty:
        raise Paso1Error("El archivo 'BBDD_Sesion-PT-INAVARRO' está vacío (sin filas).")

    col_proyecto = _find_column(df_jira, JIRA_PROYECTO_ALIAS)
    col_num_sol = BBDD_COLUMN_NUMERO_SOLICITUD
    numeros = _unique_numero_solicitud_sorted(df_bbdd[col_num_sol])
    lista: List[Dict[str, Any]] = []

    for num_sol in numeros:
        mask_sol = df_bbdd[col_num_sol].astype(str) == str(num_sol)
        bbdd_rep = df_bbdd[mask_sol].iloc[0]
        producto_base_linea = str(bbdd_rep.get(BBDD_COLUMN_PRODUCTO_BASE, "")).strip()
        descripcion_partida_diseno = str(
            bbdd_rep.get(BBDD_COLUMN_DESCRIPCION, "")
        ).strip()
        responsable = (
            str(bbdd_rep.get(BBDD_COLUMN_RESPONSABLE, "")).strip()
            if BBDD_COLUMN_RESPONSABLE in df_bbdd.columns
            else ""
        )
        tipo = (
            str(bbdd_rep.get(BBDD_COLUMN_TIPO, "")).strip()
            if BBDD_COLUMN_TIPO in df_bbdd.columns
            else "Interna"
        )
        if not tipo:
            tipo = "Interna"

        id_ensayo_detectado = _get_id_ensayo_from_bbdd_row(bbdd_rep, df_bbdd)
        clave_incidencia_jira = ""

        jira_row = _first_jira_row_for_producto(df_jira, col_proyecto, producto_base_linea)
        if jira_row is not None:
            clave_incidencia_jira = str(jira_row.get("Clave de incidencia", "")).strip()
            if not id_ensayo_detectado and clave_incidencia_jira:
                id_ensayo_detectado = clave_incidencia_jira

        # numero_solicitud: mantener tipo numérico si viene como número de la BBDD
        numero_solicitud_val = num_sol
        try:
            if isinstance(num_sol, float) and num_sol == int(num_sol):
                numero_solicitud_val = int(num_sol)
            elif isinstance(num_sol, str) and num_sol.isdigit():
                numero_solicitud_val = int(num_sol)
        except (ValueError, TypeError):
            pass

        lista.append({
            "responsable": responsable,
            "numero_solicitud": numero_solicitud_val,
            "tipo": tipo,
            "producto_base_linea": producto_base_linea,
            "descripcion_partida_diseno": descripcion_partida_diseno,
            "mapeo": {
                "id_ensayo_detectado": id_ensayo_detectado,
                "clave_incidencia_jira": clave_incidencia_jira,
            },
        })

    return {"paso_1": lista}


def build_all_paso1_from_master(
    df_solicitudes2025: pd.DataFrame,
    df_jira: pd.DataFrame,
    df_bbdd: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Construye un Paso 1 por cada fila del listado maestro Solicitudes 2025.
    Para cada solicitud: si hay datos en BBDD/Jira se rellenan; si no, cabecera mínima (Nº, tipo, nombre) para completar a mano.
    """
    col_num_2025 = _validate_solicitudes2025_columns(df_solicitudes2025)
    if df_solicitudes2025.empty:
        raise Paso1Error("El archivo 'Solicitudes 2025' no tiene filas de datos.")

    if not df_jira.empty:
        _validate_jira_columns(df_jira)
    if not df_bbdd.empty:
        _validate_bbdd_columns_for_master(df_bbdd)

    col_proyecto = _find_column(df_jira, JIRA_PROYECTO_ALIAS) if not df_jira.empty else None
    rows_master = _iter_solicitudes2025_rows(df_solicitudes2025)
    lista: List[Dict[str, Any]] = []

    for row_2025 in rows_master:
        num_sol_raw = row_2025.get(col_num_2025)
        if num_sol_raw is None or (isinstance(num_sol_raw, float) and pd.isna(num_sol_raw)):
            continue
        num_sol_str = str(num_sol_raw).strip()
        if not num_sol_str:
            continue

        nombre = str(row_2025.get(SOLICITUDES2025_COL_NOMBRE, "") or "").strip()
        solicitante = ""
        if SOLICITUDES2025_COL_SOLICITANTE in df_solicitudes2025.columns:
            solicitante = str(row_2025.get(SOLICITUDES2025_COL_SOLICITANTE, "") or "").strip().lower()

        if "extern" in solicitante:
            tipo = "Externa"
        else:
            tipo = "Interna"

        numero_solicitud_val: Any = num_sol_raw
        try:
            n = int(float(num_sol_str))
            numero_solicitud_val = n
        except (ValueError, TypeError):
            numero_solicitud_val = num_sol_str

        producto_base_linea = nombre
        descripcion_partida_diseno = ""
        responsable = ""
        id_ensayo_detectado = ""

        bbdd_rep = _get_bbdd_representative_row_for_nombre(
            df_bbdd, df_jira, col_proyecto, nombre
        )
        if bbdd_rep is not None:
            descripcion_partida_diseno = str(bbdd_rep.get(BBDD_COLUMN_DESCRIPCION, "") or "").strip()
            responsable = (
                str(bbdd_rep.get(BBDD_COLUMN_RESPONSABLE, "") or "").strip()
                if BBDD_COLUMN_RESPONSABLE in df_bbdd.columns
                else ""
            )
            if BBDD_COLUMN_TIPO in df_bbdd.columns:
                t = str(bbdd_rep.get(BBDD_COLUMN_TIPO, "") or "").strip()
                if t:
                    tipo = t
            id_ensayo_detectado = _get_id_ensayo_from_bbdd_row(bbdd_rep, df_bbdd)

        clave_incidencia_jira = ""
        if col_proyecto and producto_base_linea:
            jira_row = _first_jira_row_for_producto(df_jira, col_proyecto, producto_base_linea)
            if jira_row is not None:
                clave_incidencia_jira = str(jira_row.get("Clave de incidencia", "") or "").strip()
                if not id_ensayo_detectado and clave_incidencia_jira:
                    id_ensayo_detectado = clave_incidencia_jira

        lista.append({
            "responsable": responsable,
            "numero_solicitud": numero_solicitud_val,
            "tipo": tipo,
            "producto_base_linea": producto_base_linea,
            "descripcion_partida_diseno": descripcion_partida_diseno,
            "mapeo": {
                "id_ensayo_detectado": id_ensayo_detectado,
                "clave_incidencia_jira": clave_incidencia_jira,
            },
        })

    return {"paso_1": lista}
