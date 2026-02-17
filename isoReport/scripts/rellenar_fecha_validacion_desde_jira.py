"""
Rellena validacion.fecha_validacion en el JSON de solicitudes usando el listado Jira.

Para cada paso_1 con formula_ok con formato "ID-XXX || ...", hace match con la columna
"Clave de incidencia" del Excel. Solo usa filas con Estado = LIBERADO y toma la columna
"Fecha de vencimiento" para rellenar anexo_f10_03.validacion.fecha_validacion (formato DD/MM/YYYY).

Uso:
  python -m scripts.rellenar_fecha_validacion_desde_jira
  python -m scripts.rellenar_fecha_validacion_desde_jira --json "docs/bbdd 17.02.26.json" --excel "docs/listado jira iso.xlsx"
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


# =========================
# HELPERS
# =========================
MESES_ES = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "oct": "10", "nov": "11", "dic": "12",
}


def extraer_id_jira(formula_ok: str):
    """Extrae ID tipo ID-14 desde texto formula_ok."""
    if not formula_ok or pd.isna(formula_ok):
        return None
    m = re.search(r"ID-\d+", str(formula_ok))
    return m.group(0) if m else None


def parse_fecha_resuelta(valor):
    """
    Devuelve fecha en formato dd/mm/yyyy a partir de:
    - Timestamp
    - datetime
    - string tipo '24/abr/25 12:48 PM'
    - string tipo '10/02/2026'
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or (isinstance(valor, str) and valor.strip() == ""):
        return None

    # Si ya es Timestamp/datetime
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")

    s = str(valor).strip().lower()

    # Caso: '24/abr/25 12:48 PM'  (o sin hora)
    m = re.match(r"(\d{1,2})/([a-zñ]{3})/(\d{2,4})(.*)", s)
    if m:
        dd = m.group(1).zfill(2)
        mon_txt = m.group(2)
        yy = m.group(3)
        resto = m.group(4).strip()

        if mon_txt in MESES_ES:
            mm = MESES_ES[mon_txt]
        else:
            return None

        if len(yy) == 2:
            yyyy = "20" + yy
        else:
            yyyy = yy

        normal = f"{dd}/{mm}/{yyyy}"
        if resto:
            normal = f"{normal} {resto}"

        for fmt in ("%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(normal, fmt)
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                pass
        return None

    # Caso: '24/04/2025 12:48 PM' o '10/02/2026'
    for fmt in ("%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass

    try:
        dt = pd.to_datetime(valor, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return None


def _normalize_id(s: str) -> str:
    return str(s or "").strip()


def _id_from_formula_ok(formula_ok: str) -> str:
    """Extrae el ID antes de ' || ' en formula_ok."""
    if not formula_ok or " || " not in formula_ok:
        return ""
    return formula_ok.split(" || ", 1)[0].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Rellena fecha_validacion desde listado Jira.")
    parser.add_argument("--json", default="docs/bbdd 17.02.26.json", help="Ruta al JSON de solicitudes")
    parser.add_argument("--excel", default="docs/listado jira iso.xlsx", help="Ruta al Excel listado Jira")
    parser.add_argument("--guardar", action="store_true", help="Guardar las fechas en el JSON (por defecto solo se muestran)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    json_path = base / args.json
    excel_path = base / args.excel

    if not json_path.exists():
        raise SystemExit(f"No existe el JSON: {json_path}")
    if not excel_path.exists():
        raise SystemExit(f"No existe el Excel: {excel_path}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    try:
        df_jira = pd.read_excel(excel_path, sheet_name=0, engine="openpyxl")
    except PermissionError:
        raise SystemExit(
            "No se puede leer el Excel (permiso denegado). Cierra el archivo 'listado jira iso.xlsx' si lo tienes abierto y vuelve a ejecutar."
        )
    df_jira.columns = [str(c).strip() for c in df_jira.columns]

    if "Clave de incidencia" not in df_jira.columns:
        raise SystemExit("En el Excel falta la columna 'Clave de incidencia'.")
    col_fecha = "Fecha de vencimiento"
    if col_fecha not in df_jira.columns:
        raise SystemExit("En el Excel falta la columna 'Fecha de vencimiento'.")
    col_estado = "Estado"
    if col_estado not in df_jira.columns:
        raise SystemExit("En el Excel falta la columna 'Estado'.")

    # Solo filas LIBERADAS: por cada Clave con Estado = LIBERADO, usar Fecha de vencimiento.
    # Si hay varias filas LIBERADO para la misma clave, quedarnos con la de fecha más reciente.
    clave_to_row: dict[str, pd.Series] = {}
    for idx, row in df_jira.iterrows():
        estado = str(row.get(col_estado, "") or "").strip().upper()
        if estado != "LIBERADO":
            continue
        clave = _normalize_id(row.get("Clave de incidencia"))
        if not clave:
            continue
        valor_fecha = row.get(col_fecha)
        fecha_str = parse_fecha_resuelta(valor_fecha)
        if fecha_str is None or not fecha_str:
            if clave not in clave_to_row:
                clave_to_row[clave] = row
            continue
        if clave not in clave_to_row:
            clave_to_row[clave] = row
            continue
        try:
            d_new = datetime.strptime(fecha_str, "%d/%m/%Y")
            row_old = clave_to_row[clave]
            fecha_old = parse_fecha_resuelta(row_old.get(col_fecha))
            if fecha_old:
                d_old = datetime.strptime(fecha_old, "%d/%m/%Y")
                if d_new > d_old:
                    clave_to_row[clave] = row
        except ValueError:
            pass

    paso_1_list = data.get("paso_1") or []
    updated = 0
    listado = []
    for p1 in paso_1_list:
        vd = p1.get("verificacion_diseno")
        if not isinstance(vd, dict):
            continue
        formula_ok = (vd.get("formula_ok") or "").strip()
        id_ok = extraer_id_jira(formula_ok) or _id_from_formula_ok(formula_ok)
        if not id_ok:
            continue
        row = clave_to_row.get(_normalize_id(id_ok))
        if row is None:
            continue
        valor_fecha = row.get(col_fecha)
        fecha_str = parse_fecha_resuelta(valor_fecha)
        if fecha_str is None or not fecha_str:
            continue

        listado.append((id_ok, id_ok, fecha_str, valor_fecha))
        if args.guardar:
            if "anexo_f10_03" not in p1 or not isinstance(p1["anexo_f10_03"], dict):
                p1["anexo_f10_03"] = {}
            a = p1["anexo_f10_03"]
            if "validacion" not in a or not isinstance(a["validacion"], dict):
                a["validacion"] = {}
            a["validacion"]["fecha_validacion"] = fecha_str
        updated += 1

    print("Listado: Id Jira | Id BBDD | Fecha de vencimiento (Excel, solo LIBERADO) -> Fecha (dd/mm/yyyy)")
    print("-" * 80)
    for item in listado:
        id_jira, id_bbdd, fecha, raw = item[0], item[1], item[2], item[3]
        raw_str = str(raw).strip() if raw is not None and not (isinstance(raw, float) and pd.isna(raw)) else ""
        print(f"  {id_jira}\t{id_bbdd}\tFecha venc.: {raw_str}\t-> Fecha: {fecha}")
    print("-" * 80)
    print(f"Total: {updated} coincidencias.")

    if not args.guardar:
        print("\nPara guardar estas fechas en el JSON ejecuta: python -m scripts.rellenar_fecha_validacion_desde_jira --guardar")
        return

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado en {json_path}.")


if __name__ == "__main__":
    main()
