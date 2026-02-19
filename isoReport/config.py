"""
Configuración centralizada de rutas para la app F10.
Paths fijos; sin selector de archivos en UI.
"""

from pathlib import Path

# Raíz del proyecto (directorio donde está app.py y config.py)
PROJECT_ROOT = Path(__file__).resolve().parent

# JSON de trabajo (fuente de verdad: solicitudes con f10_01, f10_02, f10_03)
def _json_path() -> Path:
    p = PROJECT_ROOT / "data" / "solicitudes.json"
    if p.exists():
        return p
    p2u = PROJECT_ROOT / "docs" / "bbdd_18.02.26.json"
    return p2u if p2u.exists() else PROJECT_ROOT / "docs" / "bbdd 18.02.26.json"

DEFAULT_JSON_PATH = _json_path()

# F10-01: CSV por año (viabilidad y planificación; solo lectura)
# Se buscan archivos docs/F10-01*__<año>.csv (ej. F10-01 Viabilidad y planificación de diseños__2025.csv)
DEFAULT_F10_01_DIR = PROJECT_ROOT / "docs"
F10_01_CSV_PATTERN = "F10-01*__*.csv"

# Plantillas para exportación (modo provisional: se genera por código; paths por si en el futuro se rellenan)
DEFAULT_F10_02_TEMPLATE_PATH = PROJECT_ROOT / "docs" / "F10-02_ Diseño producto_ V1.xlsx"
DEFAULT_F10_03_TEMPLATE_PATH = PROJECT_ROOT / "docs" / "F10-03_ Validación producto_V1.xlsx"
