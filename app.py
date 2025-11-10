import streamlit as st
import pandas as pd

from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu

from src.db_records import get_records_wellness_db

from src.util import clean_df
from src.ui_app import (
    get_default_period,
    filter_df_by_period,
    calc_metric_block,
    calc_alertas,
    render_metric_cards,
    generar_resumen_periodo,
    show_interpretation,
    mostrar_resumen_tecnico
)

import src.config as config
config.init_config()

# ============================================================
# 🔐 AUTENTICACIÓN
# ============================================================
init_app_state()
validate_login()

if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header("Resumen de :red[Wellness]", divider="red")
menu()

#st.session_state.clear()

# ============================================================
# 📦 CARGA DE DATOS
# ============================================================
df = get_records_wellness_db()
if df.empty:
    st.warning("No hay registros de Wellness o RPE disponibles.")
    st.stop()

df["fecha_hora_registro"] = pd.to_datetime(df["fecha_hora_registro"], errors="coerce")
df["fecha_dia"] = df["fecha_hora_registro"].dt.date
df["semana"] = df["fecha_hora_registro"].dt.isocalendar().week
df["mes"] = df["fecha_hora_registro"].dt.month
df["wellness_score"] = df[["recuperacion", "energia", "sueno", "stress", "dolor"]].sum(axis=1)

# ============================================================
# 🧭 INTERFAZ PRINCIPAL
# ============================================================

default_period = get_default_period(df)
periodo = st.radio(
    "Periodo:",
    ["Hoy", "Último día", "Semana", "Mes"],
    horizontal=True,
    index=["Hoy", "Último día", "Semana", "Mes"].index(default_period)
)
df_periodo, articulo = filter_df_by_period(df, periodo)

# Cálculos principales
wellness_prom, chart_wellness, delta_wellness = calc_metric_block(df_periodo, periodo, "wellness_score", "mean")
rpe_prom, chart_rpe, delta_rpe = calc_metric_block(df_periodo, periodo, "rpe", "mean")
ua_total, chart_ua, delta_ua = calc_metric_block(df_periodo, periodo, "ua", "sum")
alertas_count, total_jugadoras, alertas_pct, chart_alertas, delta_alertas = calc_alertas(df_periodo, df, periodo)

# ============================================================
# 💠 TARJETAS DE MÉTRICAS
# ============================================================
render_metric_cards(wellness_prom, delta_wellness, chart_wellness, rpe_prom, delta_rpe, chart_rpe, ua_total, delta_ua, chart_ua, alertas_count, total_jugadoras, alertas_pct, chart_alertas, delta_alertas, articulo)

# ============================================================
# 📋 INTERPRETACIÓN Y RESUMEN TÉCNICO
# ============================================================
show_interpretation(wellness_prom, rpe_prom, ua_total, alertas_count, alertas_pct, delta_ua, total_jugadoras)

mostrar_resumen_tecnico(wellness_prom, rpe_prom, ua_total, alertas_count, total_jugadoras)

# ============================================================
# 📊 REGISTROS DEL PERIODO
# ============================================================

st.divider()
st.markdown(f"**Registros del periodo seleccionado ({periodo})**")
tabs = st.tabs([
        ":material/physical_therapy: Indicadores de bienestar y carga",
        ":material/description: Registros detallados",
        #"Riesgo de lesión"
    ])

with tabs[0]: 
    generar_resumen_periodo(df_periodo)
with tabs[1]: 
    if df_periodo.empty:
        st.info("No hay registros disponibles en este periodo.")
        st.stop()
    st.dataframe(clean_df(df_periodo), hide_index=True)