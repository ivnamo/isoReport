# App F10 — Gestión F10-01 / F10-02 / F10-03

Aplicación Streamlit para gestionar:

- **F10-01** (Viabilidad y planificación de diseños): solo lectura desde Excel; una hoja por año.
- **F10-02** (Diseño producto) y **F10-03** (Validación producto): lectura y edición desde JSON; exportación a XLSX.

## Requisitos

- Python 3.10+
- Dependencias: `streamlit`, `pandas`, `openpyxl`

```powershell
cd isoReport
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución

Desde la raíz del proyecto `isoReport`:

```powershell
cd isoReport
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

O con doble clic en `scripts/run_streamlit.bat` si existe.

## Estructura del proyecto

- **app.py** — Punto de entrada: sidebar (filtros, listado de solicitudes), área principal con pestañas.
- **config.py** — Rutas por defecto: JSON en `docs/bbdd 18.02.26.json` (o `docs/bbdd_18.02.26.json`), Excel F10-01 y plantillas en `docs/`.
- **services/** — Carga Excel F10-01 por hoja, carga/guardado atómico del JSON, construcción de la lista unificada.
- **models/** — Modelo `Solicitud` (vista unificada) y mapeo con paso_1/paso_2.
- **ui/** — Tabs F10-01 (solo lectura), F10-02 y F10-03 (edición + guardar), Exportar (generar XLSX).
- **exporters/** — Generación de XLSX F10-02 y F10-03 (modo provisional: workbook generado por código).
- **utils/** — Normalización de número de solicitud, parseo de fórmula pegada, datos compartidos (ANEXO F10-03).
- **legacy/** — Código anterior (generador JSON, editor antiguo) sin uso en la nueva interfaz.

## Estructura de datos

### JSON (fuente de verdad para F10-02 y F10-03)

- Raíz: `{"paso_1": [...], "paso_2": [...]}`.
- **paso_1**: por solicitud: `numero_solicitud`, `responsable`, `tipo`, `producto_base_linea`, `descripcion_partida_diseno`, `verificacion_diseno` (producto_final, formula_ok, riquezas), `anexo_f10_03` (especificacion_final, validacion con filas).
- **paso_2**: por solicitud: `numero_solicitud`, `producto_base_linea`, `ensayos[]` (id, ensayo, fecha, resultado, motivo_comentario, formula[{materia_prima, porcentaje_peso}]).
- Enlace: por `numero_solicitud` (canónico) y opcionalmente `producto_base_linea`.

### Excel F10-01

- Una hoja por año (nombre de hoja = "2025", "2024", etc.).
- Primera fila = cabecera. Columnas esperadas: Nº Solicitud, Solicitante, Nombre proyecto, Necesidad, País destino, Aceptado, Finalizado, etc.
- Enlace con JSON: número canónico (ej. "24/2025" → 24; "1" → 1).

### Mapeo lógico

- **F10-02** ↔ JSON: datos de partida → `paso_1.descripcion_partida_diseno`; ensayos → `paso_2.ensayos`; verificación → `paso_1.verificacion_diseno`.
- **F10-03** ↔ JSON: especificación final → `paso_1.anexo_f10_03.especificacion_final`; validación → `paso_1.anexo_f10_03.validacion` (fecha_validacion, filas).

## Añadir nuevos años en F10-01

Añade una nueva hoja en el Excel "F10-01 Viabilidad y planificación de diseños.xlsx" con el nombre del año (ej. "2026"). La app detecta las hojas numéricas (2000–2100) y las muestra en el selector de año en el sidebar.

## Notas

- Guardado del JSON: atómico (escritura en `.tmp` y renombrado).
- Exportación F10-02 y F10-03: por ahora se genera un XLSX con la misma estructura lógica desde código; en el futuro se puede sustituir por relleno de plantillas .xlsx cuando exista un mapa de celdas.
- Si una solicitud existe en F10-01 pero no en el JSON, se puede usar **Inicializar en bbdd** para crear el registro mínimo y guardarlo.
