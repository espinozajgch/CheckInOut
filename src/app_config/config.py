import streamlit as st
from auth_system.auth_core import bootstrap_auth_from_cookie, init_app_state, validate_login
from auth_system.auth_ui import login_view, menu

def init_config():
    # Streamlit page config
    st.set_page_config(page_title="Dux Logroño - Wellness & RPE", page_icon="assets/images/logo_transparente.png", layout="wide")

    # # ============================================================
    # # 🔐 AUTENTICACIÓN
    # # ============================================================
    init_app_state()
    bootstrap_auth_from_cookie()
    is_valid = validate_login()

    if not is_valid or not st.session_state["auth"]["is_logged_in"]:
        login_view()
        st.stop()

    menu()