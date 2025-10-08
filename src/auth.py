import os
from typing import Tuple
import streamlit as st
from dotenv import load_dotenv

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
    load_dotenv()
    user = os.getenv("TRAINER_USER", "admin")
    pwd = os.getenv("TRAINER_PASS", "admin")
    return user, pwd

def login_view() -> None:
    """Render the login form and handle authentication."""
    
    expected_user, expected_pass = _get_credentials()
    
    _, col2, _ = st.columns([2, 1.5, 2])

    with col2:
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
    if st.button("Cerrar sesión"):
        st.session_state["auth"] = {"is_logged_in": False, "username": ""}
        st.rerun()
