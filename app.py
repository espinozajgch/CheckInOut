import streamlit as st
from src.io_files import get_records_df
from src.ui_components import checkin_view, home_view, individual_report_view

import src.config as config
config.init_config()


from src.auth import init_app_state, login_view, menu, validate_login
init_app_state()

validate_login()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()


st.header("Respuestas :red[Check-in]", divider="red")
menu()

df = get_records_df()
home_view(df)
