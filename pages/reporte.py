import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import individual_report_view, selection_header
from src.io_files import get_records_df, load_jugadoras, load_competiciones

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('Reporte :red[Individual]', divider=True)

menu()

jug_df, jug_error = load_jugadoras()
comp_df, comp_error = load_competiciones()

jugadora, tipo, turno = selection_header(jug_df, comp_df, modo="reporte")

if not jugadora:
    st.info("Selecciona una jugadora para continuar.")
    st.stop()

#st.dataframe(jugadora)

df = get_records_df()

individual_report_view(df, jugadora)