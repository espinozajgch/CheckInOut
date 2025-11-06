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
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()
df = get_records_wellness_db()

df_filtrado, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, df, modo="reporte")

rpe_view(df_filtrado, jugadora, turno, start, end)
