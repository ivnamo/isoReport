## Generador de Informes ISO (F10-02 / F10-03)

Aplicación Streamlit para:

- Registrar diseños y ensayos (F10-02 / F10-03) a partir de recetas pegadas.
- Combinar **Solicitudes 2025**, **BBDD F10-02** y **exportación Jira**.
- Generar informes ISO en:
  - CSV maquetado (compatible con tu flujo actual).
  - Excel (`.xlsx`) con un layout similar a tu plantilla `Informe_ISO_todas_solicitudes`.

### Requisitos

```bash
pip install -r requirements.txt
```

### Ejecución

Desde este directorio:

```bash
streamlit run app.py
```

### Flujo básico

1. **Registro F10-02/F10-03**
   - Opcionalmente carga una BBDD existente (CSV).
   - Selecciona un `Nº Solicitud` desde `Solicitudes 2025.xlsx`.
   - Registra nuevos ensayos pegando la receta (`Materia prima` + `% peso`).
   - Descarga la BBDD consolidada.

2. **Generación de informes ISO**
   - Sube:
     - `Solicitudes 2025.xlsx`.
     - BBDD F10-02 (CSV).
     - Exportación `Jira.csv`.
   - Elige un `Nº Solicitud`.
   - Selecciona, si es necesario, la issue Jira **LIBERADA** que actuará como fórmula OK.
   - Descarga el informe en:
     - CSV maquetado.
     - Excel (`.xlsx`) listo para revisión/auditoría.

