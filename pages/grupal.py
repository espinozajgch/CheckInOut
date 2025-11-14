import streamlit as st
import src.config as config

from src.i18n.i18n import t
from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu

config.init_config()
init_app_state()
validate_login()

from src.ui_components import selection_header
from src.reportes.ui_grupal import group_dashboard
from src.db_records import get_records_wellness_db, load_jugadoras_db, load_competiciones_db

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

#st.header('Riesgo de :red[lesión (proximidad)]', divider="red")
st.header(t("Análisis :red[grupal]"), divider="red")

menu()

# Load reference data
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()
wellness_df = get_records_wellness_db()

#st.dataframe(wellness_df, hide_index=True)    

df, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, wellness_df, modo="reporte_grupal")
group_dashboard(df)
