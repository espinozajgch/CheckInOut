import streamlit as st
import pandas as pd
import numpy as np
from .metrics import compute_rpe_metrics, RPEFilters

import plotly.express as px
import plotly.graph_objects as go

def rpe_view(df: pd.DataFrame, jug_sel, turno_sel, start, end) -> None:
    """Página de análisis individual de cargas y RPE por jugadora."""

    # --- Calcular métricas generales ---
    flt = RPEFilters(jugadores=jug_sel or None, turnos=turno_sel or None, start=start, end=end)
    metrics = compute_rpe_metrics(df, flt)

    # --- Validar datos ---
    if df is None or df.empty:
        st.info("No hay registros disponibles para análisis individual.")
        return

    # --- Resumen general ---
    st.divider()
    st.markdown("### **Resumen de carga individual**")
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.metric("Minutos último día", value=(f"{metrics['minutos_sesion']:.0f}" if pd.notna(metrics['minutos_sesion']) else "-"))
        st.metric("Carga mes", help="Control de mesociclo", value=(f"{metrics['carga_mes']:.0f}" if metrics["carga_mes"] is not None else "-"))
    with k2:
        st.metric("UA total último día", help="Intensidad del entrenamiento o partido", value=(f"{metrics['ua_total_dia']:.0f}" if metrics["ua_total_dia"] is not None else "-"))
        st.metric("Carga media mes", help="Control de mesociclo", value=(f"{metrics['carga_media_mes']:.2f}" if metrics["carga_media_mes"] is not None else "-"))
    with k3:
        st.metric("Carga semana", help="Volumen del microciclo", value=(f"{metrics['carga_semana']:.0f}" if metrics["carga_semana"] is not None else "-"))
        st.metric("Fatiga aguda (7d)", help="Estrés agudo", value=(f"{metrics['fatiga_aguda']:.0f}" if metrics["fatiga_aguda"] is not None else "-"))
    with k4:
        st.metric("Carga media semana", help="Control semanal equilibrado", value=(f"{metrics['carga_media_semana']:.2f}" if metrics["carga_media_semana"] is not None else "-"))
        st.metric("Fatiga crónica (28d)", help="Nivel de adaptación (Media)", value=(f"{metrics['fatiga_cronica']:.1f}" if metrics["fatiga_cronica"] is not None else "-"))
    with k5:
        st.metric("Monotonía semana", help="Detectar sesiones demasiado parecidas", value=(f"{metrics['monotonia_semana']:.2f}" if metrics["monotonia_semana"] is not None else "-"))
        st.metric("Adaptación", help="Balance entre fatiga aguda y crónica", value=(f"{metrics['adaptacion']:.2f}" if metrics["adaptacion"] is not None else "-"))
    with k6:
        st.metric("Variabilidad semanal", help="Índice de variabilidad semanal", value=(f"{metrics['variabilidad_semana']:.2f}" if metrics["variabilidad_semana"] is not None else "-"))
        st.metric("ACWR", help="Relación entre fatiga aguda y crónica", value=(f"{metrics['acwr']:.2f}" if metrics["acwr"] is not None else "-"))

    resumen = get_resumen_tecnico_carga(metrics)
    st.markdown(resumen, unsafe_allow_html=True)

    graficos_individuales(df)

def graficos_individuales(df: pd.DataFrame):
    """Gráficos individuales para análisis de carga, bienestar y riesgo de lesión."""

    if df is None or df.empty:
        st.info("No hay datos disponibles para graficar.")
        return

    # Usar el df ya filtrado por jugadora
    df_player = df.copy()
    df_player = df_player.sort_values("fecha_sesion")

    st.divider()
    st.markdown("### 📈 **Gráficos individuales**")

    tabs = st.tabs([
        "RPE y UA", 
        "Carga interna y minutos", 
        "Fatiga y ACWR", 
        "Wellness (1–5)", 
        "Riesgo de lesión"
    ])

    # 1️⃣ TAB: RPE y UA
    with tabs[0]:
        st.markdown("#### Evolución de RPE y Carga Interna (UA)")
        if not df_player.empty and "ua" in df_player.columns and "rpe" in df_player.columns:
            fig_rpe = px.bar(
                df_player,
                x="fecha_sesion",
                y="ua",
                color="rpe",
                color_continuous_scale="RdYlGn_r",
                labels={"ua": "Carga Interna (UA)", "fecha_sesion": "Fecha", "rpe": "RPE"},
                title="UA (barras) y RPE (color)"
            )
            st.plotly_chart(fig_rpe)
        else:
            st.info("No hay datos de RPE o UA para graficar.")

    # 2️⃣ TAB: Carga vs minutos
    with tabs[1]:
        st.markdown("#### Relación entre duración y esfuerzo percibido")
        if "minutos_sesion" in df_player.columns and "rpe" in df_player.columns:
            fig_mix = go.Figure()
            fig_mix.add_trace(go.Bar(
                x=df_player["fecha_sesion"],
                y=df_player["minutos_sesion"],
                name="Minutos",
                marker_color="#1976D2"
            ))
            fig_mix.add_trace(go.Scatter(
                x=df_player["fecha_sesion"],
                y=df_player["rpe"],
                mode="lines+markers",
                name="RPE",
                yaxis="y2",
                line=dict(color="#E64A19", width=3)
            ))
            fig_mix.update_layout(
                title="Duración vs RPE por día",
                yaxis=dict(title="Minutos de sesión"),
                yaxis2=dict(title="RPE", overlaying="y", side="right"),
                legend_title_text="Variables"
            )
            st.plotly_chart(fig_mix)
        else:
            st.info("No hay datos de minutos o RPE para graficar.")

    # 3️⃣ TAB: Fatiga y ACWR
    with tabs[2]:
        st.markdown("#### Evolución del índice ACWR (Relación Agudo:Crónico)")
        if "ua" in df_player.columns:
            df_acwr = df_player.copy()
            df_acwr["ua"] = pd.to_numeric(df_acwr["ua"], errors="coerce")
            df_acwr["acute7"] = df_acwr["ua"].rolling(7, min_periods=3).mean()
            df_acwr["chronic28"] = df_acwr["ua"].rolling(28, min_periods=7).mean()
            df_acwr["acwr"] = df_acwr["acute7"] / df_acwr["chronic28"]
            df_acwr = df_acwr.dropna(subset=["acwr"])
            if not df_acwr.empty:
                fig_acwr = px.line(df_acwr, x="fecha_sesion", y="acwr", markers=True,
                                   title="Evolución del ACWR (7d / 28d)",
                                   labels={"acwr": "ACWR", "fecha_sesion": "Fecha"})
                fig_acwr.add_hrect(y0=0.8, y1=1.3, fillcolor="#C8E6C9", opacity=0.3, line_width=0)
                fig_acwr.add_hrect(y0=1.5, y1=3, fillcolor="#FFCDD2", opacity=0.3, line_width=0)
                st.plotly_chart(fig_acwr)
            else:
                st.info("No hay suficientes datos para calcular ACWR.")
        else:
            st.info("No hay datos de carga interna (UA) para calcular ACWR.")

    # 4️⃣ TAB: Wellness
    with tabs[3]:
        st.markdown("#### Evolución de los indicadores de bienestar (1–5)")
        cols_wellness = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
        if all(c in df_player.columns for c in cols_wellness):
            fig_wellness = px.line(
                df_player,
                x="fecha_sesion",
                y=cols_wellness,
                markers=True,
                labels={"value": "Nivel (1–5)", "fecha_sesion": "Fecha", "variable": "Parámetro"},
                title="Evolución de los componentes de Wellness"
            )
            st.plotly_chart(fig_wellness)
        else:
            st.info("No hay datos de bienestar para graficar.")

    # 5️⃣ TAB: Riesgo de lesión
    with tabs[4]:
        st.markdown("#### Riesgo de lesión basado en carga y fatiga")

        # Si tenemos datos de ACWR, fatiga o monotonía, estimamos el riesgo
        if "ua" in df_player.columns:
            df_risk = df_player.copy()
            df_risk["ua"] = pd.to_numeric(df_risk["ua"], errors="coerce")
            df_risk["acute7"] = df_risk["ua"].rolling(7, min_periods=3).mean()
            df_risk["chronic28"] = df_risk["ua"].rolling(28, min_periods=7).mean()
            df_risk["acwr"] = df_risk["acute7"] / df_risk["chronic28"]
            df_risk["fatiga"] = pd.to_numeric(df_risk.get("fatiga", np.nan), errors="coerce")

            def riesgo_calc(row):
                if pd.isna(row["acwr"]) or pd.isna(row["fatiga"]):
                    return np.nan
                if row["acwr"] > 1.5 or row["fatiga"] >= 4:
                    return "Alto"
                elif 1.3 <= row["acwr"] <= 1.5 or 3 <= row["fatiga"] < 4:
                    return "Moderado"
                else:
                    return "Bajo"

            df_risk["riesgo_lesion"] = df_risk.apply(riesgo_calc, axis=1)

            color_map = {"Bajo": "#43A047", "Moderado": "#FB8C00", "Alto": "#E53935"}
            fig_risk = px.scatter(
                df_risk,
                x="fecha_sesion",
                y="acwr",
                color="riesgo_lesion",
                color_discrete_map=color_map,
                title="Evolución del riesgo de lesión (según ACWR y fatiga)",
                labels={"acwr": "ACWR", "fecha_sesion": "Fecha", "riesgo_lesion": "Nivel de riesgo"}
            )
            fig_risk.add_hrect(y0=0.8, y1=1.3, fillcolor="#C8E6C9", opacity=0.3, line_width=0)
            st.plotly_chart(fig_risk)
        else:
            st.info("No hay datos suficientes para calcular el riesgo de lesión.")


# def rpe_view(df: pd.DataFrame, jug_sel, turno_sel, start, end) -> None:

#     flt = RPEFilters(jugadores=jug_sel or None, turnos=turno_sel or None, start=start, end=end)
#     #st.dataframe(df)
#     metrics = compute_rpe_metrics(df, flt)
#     #st.dataframe(metrics)

#     st.divider()
#     st.markdown("**Resumen**")
#     # --- KPIs de Carga Interna ---
#     k1, k2, k3, k4, k5, k6 = st.columns(6)

#     # 1️⃣ Carga inmediata
#     with k1:
#         st.metric("Minutos último día", value=(f"{metrics['minutos_sesion']:.0f}" if pd.notna(metrics['minutos_sesion']) else "-"))
#         st.metric("Carga mes", help="Control de mesociclo", value=(f"{metrics['carga_mes']:.0f}" if metrics["carga_mes"] is not None else "-"))

#     with k2:
#         st.metric("UA total último día", help="Intensidad del entrenamiento o partido", value=(f"{metrics['ua_total_dia']:.0f}" if metrics["ua_total_dia"] is not None else "-"))
#         st.metric("Carga media mes", help="Control de mesociclo", value=(f"{metrics['carga_media_mes']:.2f}" if metrics["carga_media_mes"] is not None else "-"))

#     # 2️⃣ Carga acumulada (volumen y medias)
#     with k3:
#         st.metric("Carga semana", help="Volumen del microciclo", value=(f"{metrics['carga_semana']:.0f}" if metrics["carga_semana"] is not None else "-"))
#         st.metric("Fatiga aguda (7d)", help="Estrés agudo", value=(f"{metrics['fatiga_aguda']:.0f}" if metrics["fatiga_aguda"] is not None else "-"))
#     with k4:
#         st.metric("Carga media semana", help="Control semanal equilibrado", value=(f"{metrics['carga_media_semana']:.2f}" if metrics["carga_media_semana"] is not None else "-"))
#         st.metric("Fatiga crónica (28d)", help="Nivel de adaptación (Media)", value=(f"{metrics['fatiga_cronica']:.1f}" if metrics["fatiga_cronica"] is not None else "-"))
    
#     # 3️⃣ Variabilidad y estructura del estímulo
#     with k5:
#         st.metric("Monotonía semana", help="Detectar sesiones demasiado parecidas", value=(f"{metrics['monotonia_semana']:.2f}" if metrics["monotonia_semana"] is not None else "-"))
#         st.metric("Adaptación", help="Indice de balance entre la fatiga aguda y la fatiga crónica", value=(f"{metrics['adaptacion']:.2f}" if metrics["adaptacion"] is not None else "-"))
    
#     with k6:
#         st.metric("Variabilidad semanal", help="Indice de variabilidad semanal", value=(f"{metrics['variabilidad_semana']:.2f}" if metrics["variabilidad_semana"] is not None else "-"))
#         st.metric("ACWR", help="Indice de relación entre la fatiga aguda y la fatiga crónica", value=(f"{metrics['acwr']:.2f}" if metrics["acwr"] is not None else "-"))

#     resumen = get_resumen_tecnico_carga(metrics)
#     st.markdown(resumen, unsafe_allow_html=True)

def get_resumen_tecnico_carga(metrics: dict) -> str:
    """
    Genera un resumen técnico con interpretación y colores visuales
    (rojo = riesgo, naranja = medio, verde = óptimo).
    Devuelve un texto formateado en HTML para st.markdown().
    """

    def color_text(text, color):
        return f"<b style='color:{color}'>{text}</b>"

    # --- valores base ---
    carga_semana = metrics.get("carga_semana", 0) or 0
    carga_mes = metrics.get("carga_mes", 0) or 0
    fatiga_aguda = metrics.get("fatiga_aguda", 0) or 0
    fatiga_cronica = metrics.get("fatiga_cronica", 0) or 0
    acwr = metrics.get("acwr")
    monotonia = metrics.get("monotonia_semana")
    adaptacion = metrics.get("adaptacion")
    ua_total_dia = metrics.get("ua_total_dia", 0) or 0
    minutos_dia = metrics.get("minutos_sesion", 0) or 0

    # --- CARGA SEMANAL ---
    if carga_semana > 2500:
        carga_estado = color_text("alta", "#E53935")  # rojo
    elif carga_semana >= 1500:
        carga_estado = color_text("moderada", "#FB8C00")  # naranja
    else:
        carga_estado = color_text("baja", "#43A047")  # verde

    # --- FATIGA AGUDA ---
    if fatiga_aguda > 2000:
        estado_fatiga = color_text("elevada", "#E53935")
    elif fatiga_aguda >= 1000:
        estado_fatiga = color_text("controlada", "#FB8C00")
    else:
        estado_fatiga = color_text("baja", "#43A047")

    # --- ACWR ---
    if acwr is None:
        riesgo = color_text("sin datos suficientes", "#757575")
    elif acwr > 1.5:
        riesgo = color_text("riesgo alto de sobrecarga", "#E53935")
    elif acwr < 0.8:
        riesgo = color_text("subcarga o falta de estímulo", "#FB8C00")
    else:
        riesgo = color_text("relación óptima entre carga aguda y crónica", "#43A047")

    # --- MONOTONÍA ---
    if monotonia is None:
        variabilidad = color_text("sin datos de variabilidad", "#757575")
    elif monotonia > 1.8:
        variabilidad = color_text("poca variabilidad entre sesiones", "#E53935")
    elif monotonia >= 1.5:
        variabilidad = color_text("variabilidad moderada", "#FB8C00")
    else:
        variabilidad = color_text("buena variabilidad semanal", "#43A047")

    # --- ADAPTACIÓN ---
    if adaptacion is None:
        estado_adapt = color_text("no disponible", "#757575")
    elif adaptacion < 0:
        estado_adapt = color_text("negativa (predomina la fatiga)", "#E53935")
    elif adaptacion == 0:
        estado_adapt = color_text("neutral", "#FB8C00")
    else:
        estado_adapt = color_text("positiva (asimilación adecuada del entrenamiento)", "#43A047")

    # --- construir resumen con colores ---
    resumen = (
        f":material/description: **Resumen técnico:** <div style='text-align: justify;'>En el último día registrado se completaron "
        f"{color_text(f'{minutos_dia:.0f} minutos', '#43A047')} de sesión con una carga interna de "
        f"{color_text(f'{ua_total_dia:.0f} UA', '#43A047')}. "
        f"La carga semanal actual es {carga_estado} "
        f"({color_text(f'{carga_semana:.0f} UA', '#607D8B')}) y la carga mensual acumulada asciende a "
        f"{color_text(f'{carga_mes:.0f} UA', '#607D8B')}. "
        f"La fatiga aguda es {estado_fatiga}, mientras que la fatiga crónica se mantiene en "
        f"{color_text(f'{fatiga_cronica:.1f} UA de media', '#607D8B')}, indicando una adaptación {estado_adapt}. "
        f"El índice ACWR sugiere {riesgo}, y la monotonía semanal refleja {variabilidad}."
        f"</div>"
    )

    return resumen
