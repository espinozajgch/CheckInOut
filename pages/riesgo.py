import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import risk_view
from src.io_files import get_records_df

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('Riesgo de :red[lesión (proximidad)]', divider="red")

menu()

df = get_records_df()
risk_view(df)