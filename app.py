import streamlit as st
import pandas as pd

from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu

from src.db_records import get_records_wellness_db, load_jugadoras_db

from src.util import clean_df, data_format
from src.ui_app import (
    get_default_period,
    filter_df_by_period,
    calc_metric_block,
    calc_alertas,
    render_metric_cards,
    generar_resumen_periodo,
    show_interpretation,
    mostrar_resumen_tecnico,
    get_pendientes_check
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
# CARGA DE DATOS
# ============================================================
df = get_records_wellness_db()

if df.empty:
    st.warning("No hay registros de Wellness o RPE disponibles.")
    st.stop()

df = data_format(df)
jug_df = load_jugadoras_db()
jug_df = jug_df[jug_df["plantel"] == "1FF"]

# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================
if "periodo_actual" not in st.session_state:
    st.session_state["periodo_actual"] = get_default_period(df)

opciones_periodo = ["Hoy", "Último día", "Semana", "Mes"]

periodo = st.radio(
    "Periodo:",
    opciones_periodo,
    horizontal=True,
    index=opciones_periodo.index(st.session_state["periodo_actual"])
)

if periodo != st.session_state["periodo_actual"]:
    st.session_state["periodo_actual"] = periodo

# Aplicar filtro con la opción actual
df_periodo, articulo = filter_df_by_period(df, st.session_state["periodo_actual"])

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
        ":material/report_problem: Pendientes de registro"
    ])

with tabs[0]: 
    generar_resumen_periodo(df_periodo)
with tabs[1]: 
    if df_periodo.empty:
        st.info("No hay registros disponibles en este periodo.")
        st.stop()
    st.dataframe(clean_df(df_periodo), hide_index=True)
with tabs[2]:
    if df_periodo.empty:
        st.info("No hay registros disponibles en este periodo.")
        st.stop()

    pendientes_in, pendientes_out = get_pendientes_check(df_periodo, jug_df)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(":material/login: **Sin Check-In**")
        if pendientes_in.empty:
            st.success("✅ Todas las jugadoras han realizado el check-in.")
        else:
            st.dataframe(pendientes_in, hide_index=True)

    with col2:
        st.markdown(":material/logout: **Sin Check-Out**")
        if pendientes_out.empty:
            st.success("✅ Todas las jugadoras han realizado el check-out.")
        else:
            st.dataframe(pendientes_out, hide_index=True)