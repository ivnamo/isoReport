from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .models import Ensayo, MateriaPrima


# Columnas mínimas que esperamos en una BBDD F10-02 “clásica”.
BBDD_COLUMNS_BASE = [
    "Responsable",
    "Nº Solicitud",
    "Tipo",
    "Producto base",
    "Descripción diseño",
    "ID ensayo",
    "Nombre formulación",
    "Fecha ensayo",
    "Resultado",
    "Materia prima",
    "% peso",
    "Motivo / comentario",
    "Producto final",
    "Fórmula OK",
    "Riquezas",
]


def ensure_bbdd_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garantiza que el DataFrame de BBDD tenga al menos las columnas base.
    Si alguna falta, se crea vacía.
    """
    for col in BBDD_COLUMNS_BASE:
        if col not in df.columns:
            df[col] = ""
    return df[BBDD_COLUMNS_BASE].copy()


def parse_receta_text(text: str) -> List[MateriaPrima]:
    """
    Parsea un bloque de texto con líneas del tipo:

        AGUA INICIAL\t52,58
        EDTA TETRASODICO;0,1
        GLICINA  2.1

    devolviendo una lista de MateriaPrima.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    materias: List[MateriaPrima] = []

    for line in lines:
        sep = None
        if "\t" in line:
            sep = "\t"
        elif ";" in line:
            sep = ";"
        else:
            # la coma puede ser separador o decimal, intentamos heurística simple:
            parts_tmp = line.split(",")
            if len(parts_tmp) > 2:
                sep = ","

        if sep is None:
            parts = line.split()
            if len(parts) < 2:
                continue
            pct = parts[-1]
            materia = " ".join(parts[:-1])
        else:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) < 2:
                continue
            materia, pct = parts[0], parts[1]

        materias.append(MateriaPrima(nombre=materia, porcentaje_peso=str(pct)))

    return materias


def build_new_bbdd_rows_from_receta(
    *,
    responsable: str,
    numero_solicitud: str,
    tipo: str,
    producto_base: str,
    descripcion_diseno: str,
    id_ensayo: str,
    nombre_formulacion: str,
    fecha_ensayo: str,
    resultado: str,
    motivo: str,
    producto_final: str,
    formula_ok: str,
    riquezas: str,
    materias: Iterable[MateriaPrima],
) -> pd.DataFrame:
    """
    A partir de la cabecera de proyecto y de ensayo + lista de materias,
    construye las filas que se añadirán a la BBDD F10-02.
    """
    records: List[Dict[str, str]] = []
    for m in materias:
        records.append(
            {
                "Responsable": responsable.strip(),
                "Nº Solicitud": str(numero_solicitud).strip(),
                "Tipo": tipo.strip(),
                "Producto base": producto_base.strip(),
                "Descripción diseño": descripcion_diseno.strip(),
                "ID ensayo": id_ensayo.strip(),
                "Nombre formulación": nombre_formulacion.strip(),
                "Fecha ensayo": fecha_ensayo.strip(),
                "Resultado": resultado.strip(),
                "Materia prima": m.nombre.strip(),
                "% peso": m.porcentaje_peso.strip(),
                "Motivo / comentario": motivo.strip(),
                "Producto final": producto_final.strip(),
                "Fórmula OK": formula_ok.strip(),
                "Riquezas": riquezas.strip(),
            }
        )

    return pd.DataFrame.from_records(records, columns=BBDD_COLUMNS_BASE)


def group_bbdd_by_ensayo(df_bbdd: pd.DataFrame) -> List[Ensayo]:
    """
    Reconstruye objetos Ensayo a partir de una BBDD plana F10-02.

    Agrupa por:
      (ID ensayo, Nombre formulación, Fecha ensayo, Resultado, Motivo / comentario)
    y agrega listas de materias primas y % peso.
    """
    df = ensure_bbdd_columns(df_bbdd)

    group_cols = [
        "ID ensayo",
        "Nombre formulación",
        "Fecha ensayo",
        "Resultado",
        "Motivo / comentario",
    ]

    grupos = (
        df.groupby(group_cols, dropna=False)
        .agg({"Materia prima": list, "% peso": list})
        .reset_index()
    )

    ensayos: List[Ensayo] = []
    for _, row in grupos.iterrows():
        materias: List[MateriaPrima] = []
        for mp, pct in zip(row["Materia prima"], row["% peso"]):
            materias.append(MateriaPrima(nombre=str(mp), porcentaje_peso=str(pct)))

        ensayo = Ensayo(
            id_ensayo=str(row["ID ensayo"]),
            nombre_formulacion=str(row["Nombre formulación"]),
            fecha_ensayo=str(row["Fecha ensayo"]),
            resultado=str(row["Resultado"]),
            motivo=str(row["Motivo / comentario"]),
            materias=materias,
        )
        ensayos.append(ensayo)

    return ensayos


def ensayo_to_dict_rows(ensayo: Ensayo) -> List[Dict[str, str]]:
    """
    Utilidad inversa por si se quiere volcar un Ensayo a filas de BBDD.
    """
    rows: List[Dict[str, str]] = []
    for m in ensayo.materias:
        rows.append(
            {
                "ID ensayo": ensayo.id_ensayo,
                "Nombre formulación": ensayo.nombre_formulacion,
                "Fecha ensayo": ensayo.fecha_ensayo,
                "Resultado": ensayo.resultado,
                "Motivo / comentario": ensayo.motivo,
                "Materia prima": m.nombre,
                "% peso": m.porcentaje_peso,
            }
        )
    return rows


