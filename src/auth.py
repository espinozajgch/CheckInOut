import os
from typing import Tuple
import streamlit as st
from dotenv import load_dotenv
from src.util import centered_text

def init_app_state():
    ensure_session_defaults()
    if "flash" not in st.session_state:
        st.session_state["flash"] = None

def ensure_session_defaults() -> None:
    """Initialize session state defaults for authentication and UI."""
    if "auth" not in st.session_state:
        st.session_state["auth"] = {
            "is_logged_in": False,
            "username": "",
        }

def _get_credentials() -> Tuple[str, str]:
    """Load credentials from environment or fallback to hardcoded defaults.

    Environment variables (optional): TRAINER_USER, TRAINER_PASS
    Defaults: admin / admin
    """
    #load_dotenv()
    # user = os.getenv("TRAINER_USER", "admin")
    # pwd = os.getenv("TRAINER_PASS", "admin")
    user = st.secrets.db.username
    pwd = st.secrets.db.password
    return user, pwd

def login_view() -> None:
    """Render the login form and handle authentication."""
    
    expected_user, expected_pass = _get_credentials()
    
    _, col2, _ = st.columns([2, 1.5, 2])

    with col2:
        st.markdown("""
            <style>
                [data-testid="stSidebar"] {
                    display: none;
                    visibility: hidden;
                },
                [data-testid="st-emotion-cache-169dgwr edtmxes15"] {
                    display: none;
                    visibility: hidden;
                }
                [data-testid="stBaseButton-headerNoPadding"] {
                    display: none;
                    visibility: hidden;
                }
            </style>
        """, unsafe_allow_html=True)

        st.header('Login :red[Entrenador]')

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario", value="")
            password = st.text_input("Contraseña", type="password", value="")
            submitted = st.form_submit_button("Iniciar sesión", type="primary")

        if submitted:
            if username == expected_user and password == expected_pass:
                st.session_state["auth"]["is_logged_in"] = True
                st.session_state["auth"]["username"] = username
                st.success("Autenticado correctamente")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

        st.caption("Usa usuario/contraseña proporcionados o variables de entorno TRAINER_USER/TRAINER_PASS")

def logout_button() -> None:
    """Render a logout button to clear session."""
    btnSalir = st.button("Log out", type="tertiary", icon=":material/logout:")

    #if st.button("Cerrar sesión"):
    if btnSalir:
        st.session_state["auth"] = {"is_logged_in": False, "username": ""}
        st.rerun()

def menu():
    with st.sidebar:
        st.logo("assets/images/logo.png", size="large")
        st.subheader("Entrenador :material/admin_panel_settings:")
        
        #st.write(f"Usuario: {st.session_state['auth']['username']}")
        st.write(f"Hola **:blue-background[{st.session_state['auth']['username'].capitalize()}]** ")
        st.subheader("Modo :material/dashboard:")
        #
        mode = st.radio("Modo", options=["Registro", "Respuestas", "Check-in", "RPE"], index=0)
        
        st.page_link("app.py", label="Home", icon=":material/home:")
        st.page_link("pages/registros.py", label="Registro", icon=":material/app_registration:")
        st.page_link("pages/respuestas.py", label="Respuestas", icon=":material/article_person:")
        st.page_link("pages/checkin.py", label="Check-in", icon=":material/lab_profile:")
        logout_button()
        #st.divider()
        return mode