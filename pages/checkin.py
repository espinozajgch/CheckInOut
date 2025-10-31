import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import checkin_view

from src.io_files import get_records_df

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()


st.header(':red[Check-In]', divider=True)

menu()

df = get_records_df()
checkin_view(df)

