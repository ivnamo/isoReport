"""
Migración: JSON actual (paso_1/paso_2) + CSV F10-01 → nuevo JSON con estructura { "solicitudes": [...] }.

Cada solicitud tiene id, numero_solicitud, f10_01 (columnas CSV), f10_02, f10_03.
Solo se incluyen solicitudes que tienen fila en el CSV. Los pares (paso_1, paso_2) sin match
en el CSV se reportan para que el usuario decida.

Uso:
  python -m scripts.migrate_to_solicitudes_json
  python -m scripts.migrate_to_solicitudes_json --json docs/bbdd_18.02.26.json --csv "docs/F10-01 Viabilidad y planificación de diseños__2025.csv" --out data/solicitudes.json
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

# Permitir importar desde raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))



# Columnas CSV F10-01 normalizadas (PROBLEMAS sin espacio final)
F10_01_NUMERIC_KEYS = {
    "TIEMPO ESTIMADO (días laborables)",
    "HORAS EMPLEADAS I+D",
    "HORAS EMPLEADAS EN CALIDAD",
}


def _normalize_product_name(s: str) -> str:
    """Normaliza nombre de producto para comparar (como en solicitudes_unified)."""
    return (" ".join((s or "").strip().split())).replace(" ", "").upper()


def _normalize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columna: strip. PROBLEMAS con espacio -> PROBLEMAS."""
    df = df.copy()
    new_columns = []
    for c in df.columns:
        name = str(c).strip()
        if name == "PROBLEMAS " or name.endswith(" "):
            name = name.rstrip()
        new_columns.append(name)
    df.columns = new_columns
    return df


def _csv_row_to_f10_01(row: pd.Series, columns: list[str]) -> dict:
    """Convierte una fila CSV a objeto f10_01 con claves normalizadas. Numéricos como número."""
    out = {}
    for col in columns:
        val = row.get(col) if hasattr(row, "get") else getattr(row, col, None)
        if hasattr(val, "item"):  # numpy scalar
            try:
                val = val.item()
            except (ValueError, AttributeError):
                pass
        if col in F10_01_NUMERIC_KEYS:
            if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
                out[col] = None
            else:
                try:
                    s = str(val).strip().replace(",", ".")
                    out[col] = int(float(s)) if "." not in s or float(s) == int(float(s)) else float(s)
                except (ValueError, TypeError):
                    out[col] = val
        else:
            if isinstance(val, float) and pd.isna(val):
                out[col] = ""
            else:
                out[col] = val if val is not None else ""
    return out


def _canonical_ensayo(ens: dict) -> dict:
    """Solo campos canónicos: id, ensayo, fecha, resultado, motivo_comentario, formula."""
    return {
        "id": str(ens.get("id") or "").strip(),
        "ensayo": str(ens.get("ensayo") or "").strip(),
        "fecha": str(ens.get("fecha") or "").strip(),
        "resultado": str(ens.get("resultado") or "").strip(),
        "motivo_comentario": str(ens.get("motivo_comentario") or "").strip(),
        "formula": list(ens.get("formula") or []),
    }


def _build_f10_02_from_paso1_paso2(p1: dict, p2: dict) -> dict:
    """Construye f10_02 canónico desde paso_1 y paso_2."""
    ensayos = []
    for e in (p2.get("ensayos") or []):
        ensayos.append(_canonical_ensayo(e))
    v = p1.get("verificacion_diseno") or {}
    return {
        "responsable": str(p1.get("responsable") or "").strip(),
        "descripcion_partida_diseno": str(p1.get("descripcion_partida_diseno") or "").strip(),
        "ensayos": ensayos,
        "verificacion_diseno": {
            "producto_final": str(v.get("producto_final") or "").strip(),
            "formula_ok": str(v.get("formula_ok") or "").strip(),
            "riquezas": str(v.get("riquezas") or "").strip(),
        },
    }


def _build_f10_03_from_anexo(anexo: dict) -> dict:
    """Construye f10_03 desde paso_1.anexo_f10_03. Especificación: descripcion, aspecto, color, caracteristicas_quimicas."""
    if not anexo or not isinstance(anexo, dict):
        return {
            "especificacion_final": {"descripcion": "", "aspecto": "", "color": "", "caracteristicas_quimicas": ""},
            "validacion": {"fecha_validacion": "", "filas": []},
        }
    esp = anexo.get("especificacion_final") or {}
    val = anexo.get("validacion") or {}
    filas = list(val.get("filas") or [])
    return {
        "especificacion_final": {
            "descripcion": str(esp.get("descripcion") or "").strip(),
            "aspecto": str(esp.get("aspecto") or "").strip(),
            "color": str(esp.get("color") or "").strip(),
            "caracteristicas_quimicas": str(esp.get("caracteristicas_quimicas") or "").strip(),
        },
        "validacion": {
            "fecha_validacion": str(val.get("fecha_validacion") or "").strip(),
            "filas": [
                {
                    "area": str(f.get("area") or "").strip(),
                    "aspecto_a_validar": str(f.get("aspecto_a_validar") or "").strip(),
                    "validar_ok_nok": str(f.get("validar_ok_nok") or "OK").strip() or "OK",
                    "comentarios": str(f.get("comentarios") or "").strip(),
                }
                for f in filas
            ],
        },
    }


def _empty_f10_02() -> dict:
    return {
        "responsable": "",
        "descripcion_partida_diseno": "",
        "ensayos": [],
        "verificacion_diseno": {"producto_final": "", "formula_ok": "", "riquezas": ""},
    }


def _empty_f10_03() -> dict:
    return {
        "especificacion_final": {"descripcion": "", "aspecto": "", "color": "", "caracteristicas_quimicas": ""},
        "validacion": {"fecha_validacion": "", "filas": []},
    }


def run_migration(
    json_path: Path,
    csv_path: Path,
    out_path: Path | None = None,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """
    Lee JSON actual y CSV, devuelve (solicitudes, reporte_sin_match).
    reporte_sin_match: lista de (numero_solicitud, producto_base_linea) que estaban en JSON pero no tienen fila en CSV.
    """
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    paso_1_list = raw.get("paso_1") or []
    paso_2_list = raw.get("paso_2") or []

    # Índice por nombre de producto normalizado solo: norm_product -> (p1, p2)
    json_by_product = {}
    for p1 in paso_1_list:
        prod_raw = (str(p1.get("producto_base_linea") or "").strip())[:80]
        norm_prod = _normalize_product_name(prod_raw)
        if not norm_prod:
            continue
        if norm_prod not in json_by_product:
            p2 = None
            for blq in (paso_2_list or []):
                blq_prod = (str(blq.get("producto_base_linea") or "").strip())[:80]
                if _normalize_product_name(blq_prod) == norm_prod:
                    p2 = blq
                    break
            if p2 is None:
                p2 = {"ensayos": [], "numero_solicitud": p1.get("numero_solicitud"), "producto_base_linea": p1.get("producto_base_linea", ""), "clave_incidencia_jira": ""}
            json_by_product[norm_prod] = (p1, p2)

    df = pd.read_csv(csv_path, encoding="utf-8")
    df = _normalize_csv_columns(df)
    columns = list(df.columns)
    if "ID" not in columns or "Nº Solicitud" not in columns:
        raise ValueError("El CSV debe tener columnas ID y Nº Solicitud (nombres normalizados).")

    solicitudes = []
    matched_products = set()
    # id único por solicitud: 1, 2, 3, ...
    unique_id = 0

    for idx in df.index:
        unique_id += 1
        row = df.loc[idx]

        num_sol = row.get("Nº Solicitud") if hasattr(row, "get") else getattr(row, "Nº Solicitud", "")
        if num_sol is None or (isinstance(num_sol, float) and pd.isna(num_sol)):
            num_sol = ""
        num_sol = str(num_sol).strip()

        _nom = (row.get("NOMBRE") if hasattr(row, "get") else getattr(row, "NOMBRE", ""))
        _com = (row.get("NOM_COMERCIAL") if hasattr(row, "get") else getattr(row, "NOM_COMERCIAL", ""))
        nombre = (str(_nom) if _nom is not None else "").strip()[:80]
        nom_com = (str(_com) if _com is not None else "").strip()[:80]
        product_for_match = nombre or nom_com or ""

        f10_01 = _csv_row_to_f10_01(row, columns)
        f10_01["ID"] = unique_id
        norm_csv = _normalize_product_name(product_for_match)
        lookup = json_by_product.get(norm_csv) if norm_csv else None
        if lookup:
            p1, p2 = lookup
            matched_products.add(norm_csv)
            f10_02 = _build_f10_02_from_paso1_paso2(p1, p2)
            f10_03 = _build_f10_03_from_anexo(p1.get("anexo_f10_03"))
        else:
            f10_02 = _empty_f10_02()
            f10_03 = _empty_f10_03()

        solicitudes.append({
            "id": unique_id,
            "numero_solicitud": num_sol,
            "f10_01": f10_01,
            "f10_02": f10_02,
            "f10_03": f10_03,
        })

    reporte_sin_match = []
    for norm_prod, (p1, p2) in json_by_product.items():
        if norm_prod not in matched_products:
            reporte_sin_match.append((str(p1.get("numero_solicitud")), str(p1.get("producto_base_linea") or "")))

    return solicitudes, reporte_sin_match


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrar JSON paso_1/paso_2 + CSV F10-01 a JSON solicitudes[]")
    parser.add_argument("--json", default=None, help="Ruta al JSON actual (paso_1, paso_2)")
    parser.add_argument("--csv", default=None, help="Ruta al CSV F10-01 (ej. F10-01 Viabilidad...__2025.csv)")
    parser.add_argument("--out", default=None, help="Ruta de salida del nuevo JSON (por defecto se sobrescribe el de entrada con backup)")
    args = parser.parse_args()

    root = PROJECT_ROOT
    json_path = Path(args.json) if args.json else (root / "docs" / "bbdd_18.02.26.json")
    if not json_path.is_absolute():
        json_path = root / json_path
    csv_path = Path(args.csv) if args.csv else (root / "docs" / "F10-01 Viabilidad y planificación de diseños__2025.csv")
    if not csv_path.is_absolute():
        csv_path = root / csv_path
    out_path = Path(args.out) if args.out else None
    if out_path and not out_path.is_absolute():
        out_path = root / out_path

    if not json_path.exists():
        raise SystemExit(f"No se encuentra el JSON: {json_path}")
    if not csv_path.exists():
        raise SystemExit(f"No se encuentra el CSV: {csv_path}")

    solicitudes, reporte_sin_match = run_migration(json_path, csv_path, out_path)

    output = out_path or json_path
    if output == json_path:
        backup = json_path.with_suffix(json_path.suffix + ".backup")
        shutil.copy2(json_path, backup)
        print(f"Backup guardado en: {backup}")

    result = {"solicitudes": solicitudes}
    out_file = output if output else (root / "data" / "solicitudes.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Escrito {len(solicitudes)} solicitudes en: {out_file}")

    if reporte_sin_match:
        print("\n--- Bloques en el JSON sin fila en el CSV (no incluidos en el nuevo JSON) ---")
        for num, prod in reporte_sin_match:
            print(f"  numero_solicitud={num}, producto_base_linea={prod}")
    else:
        print("\nTodos los bloques del JSON tenían fila en el CSV.")


if __name__ == "__main__":
    main()
