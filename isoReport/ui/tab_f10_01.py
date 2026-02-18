"""
Tab F10-01: solo lectura. Muestra datos de la fila Excel en cards/secciones.
"""

from __future__ import annotations

from models.solicitud import Solicitud


def render_tab_f10_01(solicitud: Solicitud) -> None:
    """Renderiza el tab F10-01 (viabilidad y planificación) en solo lectura."""
    st.subheader("F10-01 — Viabilidad y planificación de diseños (solo lectura)")
    row = solicitud.f10_01_row
    if not row:
        st.info("Esta solicitud no tiene datos en F10-01 para este año (solo existe en la bbdd).")
        st.write("**Nº Solicitud:**", solicitud.numero_solicitud_canonico)
        st.write("**Producto base / línea:**", (solicitud.paso_1 or {}).get("producto_base_linea", ""))
        return

    with st.expander("Identificación", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Nº Solicitud:**", row.get("Nº Solicitud", ""))
            st.write("**Solicitante:**", row.get("Solicitante", ""))
            st.write("**Nombre proyecto:**", row.get("Nombre proyecto", ""))
        with c2:
            st.write("**País destino:**", row.get("País destino", ""))
            st.write("**Aceptado:**", row.get("Aceptado", ""))
            st.write("**Finalizado:**", row.get("Finalizado", ""))

    with st.expander("Necesidad y contexto"):
        st.write("**Necesidad:**", row.get("Necesidad", ""))
        st.write("**Producto competencia:**", row.get("Producto competencia", ""))
        st.write("**Volumen competencia:**", row.get("Volumen competencia", ""))
        st.write("**Precio competencia:**", row.get("Precio competencia", ""))
        st.write("**Volumen propuesto:**", row.get("Volumen propuesto", ""))
        st.write("**Envase:**", row.get("Envase", ""))

    with st.expander("Planificación y fechas"):
        st.write("**Fecha aprobación solicitud:**", row.get("Fecha aprobación solicitud", ""))
        st.write("**Tiempo estimado (días laborables):**", row.get("Tiempo estimado (días laborables)", ""))
        st.write("**Fecha finalización estimada:**", row.get("Fecha finalización estimada", ""))
        st.write("**Fecha finalización real:**", row.get("Fecha finalización real", ""))
        st.write("**Horas empleadas I+D:**", row.get("Horas empleadas I+D", ""))
        st.write("**Horas empleadas Calidad:**", row.get("Horas empleadas Calidad", ""))

    with st.expander("Motivo denegado"):
        st.write(row.get("Motivo denegado", "") or "—")

    with st.expander("Problemas y comentarios"):
        st.write("**Problemas:**", row.get("Problemas", "") or "—")
        st.write("**Comentarios:**", row.get("Comentarios", "") or "—")
