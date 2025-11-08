import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import risk_view, selection_header
from src.db_records import get_records_wellness_db, load_jugadoras_db, load_competiciones_db

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

#st.header('Riesgo de :red[lesión (proximidad)]', divider="red")
st.header("Análisis :red[grupal]", divider=True)

menu()

# Load reference data
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()
wellness_df = get_records_wellness_db()

df, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, wellness_df, modo="reporte")
risk_view(df, jugadora, turno, start, end)