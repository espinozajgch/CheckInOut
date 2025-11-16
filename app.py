import streamlit as st

from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu

from src.db.db_records import get_records_db, load_jugadoras_db

from src.util import clean_df, data_format
from src.ui.ui_app import (
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

from src.i18n.i18n import t
import src.app_config.config as config
config.init_config()

# ============================================================
# 🔐 AUTENTICACIÓN
# ============================================================
init_app_state()
validate_login()

if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()
menu()

st.header(t("Resumen de :red[Wellness] (1er Equipo)"), divider="red")

# ============================================================
# 📦 CARGA DE DATOS
# ============================================================
df = get_records_db()

if df.empty:
    st.warning(t("No hay registros de Wellness o RPE disponibles."))
    st.stop()

df = data_format(df)
jug_df = load_jugadoras_db()
jug_df = jug_df[jug_df["plantel"] == "1FF"]

# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================

default_period = get_default_period(df)

# Diccionario clave interna → texto traducido
OPCIONES_PERIODO = {
    "Hoy": t("Hoy"),
    "Último día": t("Último día"),
    "Semana": t("Semana"),
    "Mes": t("Mes")
}

periodo_traducido = st.radio(
    t("Periodo:"),
    list(OPCIONES_PERIODO.values()),horizontal=True,
    index=list(OPCIONES_PERIODO.keys()).index(default_period))

periodo = next(k for k, v in OPCIONES_PERIODO.items() if v == periodo_traducido)
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
st.markdown(t("**Registros del periodo seleccionado**") + f"(:blue-background[{periodo_traducido}])")
tabs = st.tabs([
        t(":material/physical_therapy: Indicadores de bienestar y carga"),
        t(":material/description: Registros detallados"),
        t(":material/report_problem: Pendientes de registro")
    ])

if df_periodo.empty:
    st.info(t("No hay registros disponibles en este periodo."))
    st.stop()

with tabs[0]: 
    generar_resumen_periodo(df_periodo)
with tabs[1]: 
    st.dataframe(clean_df(df_periodo), hide_index=True)
with tabs[2]:

    pendientes_in, pendientes_out = get_pendientes_check(df_periodo, jug_df)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(t(":material/login: **Sin Check-In**"))
        if pendientes_in.empty:
            st.success(t(":material/check_circle: Todas las jugadoras han realizado el check-in."))
        else:
            st.dataframe(pendientes_in, hide_index=True)

    with col2:
        st.markdown(t(":material/logout: **Sin Check-Out**"))
        if pendientes_out.empty:
            st.success(t(":material/check_circle: Todas las jugadoras han realizado el check-out."))
        else:
            st.dataframe(pendientes_out, hide_index=True)