import streamlit as st
import pandas as pd
import numpy as np
from .metrics import compute_rpe_metrics, RPEFilters

from .plots_individuales import (
    grafico_rpe_ua,
    grafico_duracion_rpe,
    grafico_acwr,
    grafico_wellness,
    grafico_riesgo_lesion,
    tabla_wellness_individual
)

def metricas(df: pd.DataFrame, jug_sel, turno_sel, start, end) -> None:
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

    resumen = _get_resumen_tecnico_carga(metrics)
    st.markdown(resumen, unsafe_allow_html=True)

    #st.dataframe(df)
    #tabla_wellness_individual(df)

def _get_resumen_tecnico_carga(metrics: dict) -> str:
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

def calcular_semaforo_riesgo(df: pd.DataFrame) -> tuple[str, str, float, float]:
    """
    Calcula el semáforo de riesgo basándose en ACWR (carga aguda/crónica)
    y la percepción de fatiga (1–5).

    Retorna:
        icono (str): 🟢🟠🔴⚪️
        descripcion (str): texto interpretativo
        acwr (float): índice carga aguda/crónica
        fatiga (float): último valor de fatiga
    """

    if "ua" not in df.columns:
        return "⚪️", "Sin datos de carga (UA).", np.nan, np.nan

    # Convertir UA a numérico
    df["ua"] = pd.to_numeric(df["ua"], errors="coerce")
    df = df.dropna(subset=["ua"])

    df = df.copy()
    
    # Calcular carga aguda (últimos 7 días) y crónica (últimos 28 días)
    df["acute7"] = df["ua"].rolling(7, min_periods=3).mean()
    df["chronic28"] = df["ua"].rolling(28, min_periods=7).mean()
    df["acwr"] = df["acute7"] / df["chronic28"]
    df = df.dropna(subset=["acwr"])

    # Últimos valores
    last_acwr = df["acwr"].iloc[-1] if not df.empty else np.nan
    last_fatiga = df["fatiga"].iloc[-1] if "fatiga" in df.columns else np.nan

    # Lógica de riesgo
    if pd.isna(last_acwr) and pd.isna(last_fatiga):
        return "⚪️", "Sin datos suficientes para evaluar riesgo.", np.nan, np.nan

    if last_acwr > 1.5 or (not pd.isna(last_fatiga) and last_fatiga >= 4):
        return "🔴", "Riesgo alto de sobrecarga o fatiga acumulada.", last_acwr, last_fatiga
    elif 1.3 <= last_acwr <= 1.5 or (not pd.isna(last_fatiga) and 3 <= last_fatiga < 4):
        return "🟠", "Riesgo moderado; controlar volumen y recuperación.", last_acwr, last_fatiga
    elif 0.8 <= last_acwr < 1.3 and (pd.isna(last_fatiga) or last_fatiga < 3):
        return "🟢", "Riesgo bajo; zona óptima de carga y adaptación.", last_acwr, last_fatiga
    else:
        return "⚪️", "Carga muy baja; posible desadaptación o falta de estímulo.", last_acwr, last_fatiga

def graficos_individuales(df: pd.DataFrame):
    """Gráficos individuales para análisis de carga, bienestar y riesgo."""
    if df is None or df.empty:
        st.info("No hay datos disponibles para graficar.")
        return

    df_player = df.copy().sort_values("fecha_sesion")

    #st.divider()
    st.markdown("### **Gráficos individuales**")

    tabs = st.tabs([
        "Wellness (1-5)",
        "Fatiga y ACWR",
        "RPE y UA",
        "Duración vs RPE",
        #"Riesgo de lesión"
    ])

    with tabs[0]: 
        tabla_wellness_individual(df_player)
        st.divider()
        grafico_wellness(df_player)
    with tabs[1]: 
        grafico_acwr(df_player)
    with tabs[2]: 
        grafico_rpe_ua(df_player)
    with tabs[3]: 
        grafico_duracion_rpe(df_player)
    #with tabs[4]: 
    #    grafico_riesgo_lesion(df_player)
