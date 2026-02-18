"""
Configuración centralizada de rutas para la app F10.
Paths fijos; sin selector de archivos en UI.
"""

from pathlib import Path

# Raíz del proyecto (directorio donde está app.py y config.py)
PROJECT_ROOT = Path(__file__).resolve().parent

# JSON de trabajo (fuente de verdad para F10-02 y F10-03)
def _json_path() -> Path:
    p = PROJECT_ROOT / "docs" / "bbdd 18.02.26.json"
    if p.exists():
        return p
    p2 = PROJECT_ROOT / "docs" / "bbdd_18.02.26.json"
    return p2 if p2.exists() else p

DEFAULT_JSON_PATH = _json_path()

# Excel F10-01 (viabilidad y planificación; solo lectura)
DEFAULT_F10_01_PATH = PROJECT_ROOT / "docs" / "F10-01 Viabilidad y planificación de diseños.xlsx"

# Plantillas para exportación (modo provisional: se genera por código; paths por si en el futuro se rellenan)
DEFAULT_F10_02_TEMPLATE_PATH = PROJECT_ROOT / "docs" / "F10-02_ Diseño producto_ V1.xlsx"
DEFAULT_F10_03_TEMPLATE_PATH = PROJECT_ROOT / "docs" / "F10-03_ Validación producto_V1.xlsx"
