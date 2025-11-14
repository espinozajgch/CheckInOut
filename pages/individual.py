import streamlit as st
import src.config as config


from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu
from src.i18n.i18n import t
from src.ui_components import selection_header
from src.reportes.ui_individual import metricas, graficos_individuales, calcular_semaforo_riesgo
from src.db_records import get_records_wellness_db, load_jugadoras_db, load_competiciones_db

config.init_config()
init_app_state()
validate_login()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

#st.header('RPE / :red[Cargas]', divider=True)
st.header(t("Análisis :red[individual]"), divider="red")

menu()

# Load reference data
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()
df = get_records_wellness_db()

df_filtrado, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, df, modo="reporte")

if not jugadora:
    st.info(t("Selecciona una jugadora para continuar."))
    st.stop()

    #st.subheader("RPE / Cargas")
if df_filtrado is None or df_filtrado.empty:
    st.info(t("No hay registros aún (se requieren Check-out con UA calculado)."))
    st.stop()

metricas(df_filtrado, jugadora, turno, start, end)

icon, desc, acwr, fatiga = calcular_semaforo_riesgo(df_filtrado)

st.markdown(f"{t('**Riesgo actual:**')} {icon} {desc}")
#st.dataframe(df_filtrado)
graficos_individuales(df_filtrado)