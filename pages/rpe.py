import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import rpe_view, selection_header
from src.db_records import get_records_wellness_db, load_jugadoras_db, load_competiciones_db

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('RPE / :red[Cargas]', divider=True)

menu()

# Load reference data
jug_df, jug_error = load_jugadoras_db()
comp_df, comp_error = load_competiciones_db()

if jug_error:
    st.error(jug_error)
    st.stop()

jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, modo="reporte")

df = get_records_wellness_db()
rpe_view(df, jugadora, turno, start, end)
