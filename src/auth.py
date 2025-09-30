import streamlit as st

import os
from typing import Tuple
from dotenv import load_dotenv
from src.util import centered_text

import jwt
import time
#from streamlit_cookies_manager import EncryptedCookieManager
from st_cookies_manager import EncryptedCookieManager

# # --- CONFIG JWT ---
JWT_SECRET = st.secrets.auth.jwt_secret
JWT_ALGORITHM = st.secrets.auth.algorithm
JWT_EXP_DELTA_SECONDS = st.secrets.auth.time

# # --- CONFIG COOKIES ---
cookies = EncryptedCookieManager(prefix="dux", password=JWT_SECRET)

if not cookies.ready():
    st.stop()

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
            "token": ""
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

                token = create_jwt_token(username)
                cookies["auth_token"] = token
                cookies.save()
                
                st.session_state["auth"]["is_logged_in"] = True
                st.session_state["auth"]["username"] = username
                st.session_state["auth"]["token"] = token

                st.success("Autenticado correctamente")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

        st.caption("Usa usuario/contraseña proporcionados o variables de entorno TRAINER_USER/TRAINER_PASS")

def logout():
    """Elimina sesión y cookie."""
    st.session_state["auth"] = {"is_logged_in": False, "username": "", "token": ""}
    cookies["auth_token"] = ""
    cookies.save()

    st.rerun()

def create_jwt_token(username: str):
    """Crea un token JWT firmado con expiración."""
    payload = {
        "user": username,
        "exp": time.time() + JWT_EXP_DELTA_SECONDS,
        "iat": time.time()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def get_current_user():
    """Valida token de cookie o session_state y devuelve usuario si es válido."""
    token = st.session_state['auth']['token'] or cookies.get("auth_token")
    
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        st.session_state["auth"]["is_logged_in"] = True
        st.session_state["auth"]["username"] = payload["user"]
        st.session_state["auth"]["token"] = token
        
        return payload["user"]
    except jwt.ExpiredSignatureError:
        logout()
        return None
    except jwt.InvalidTokenError:
        logout()
        return None


def validate_login():
    username = get_current_user()
    if not username:
        return False

    st.text(username)
    return username

def menu():
    with st.sidebar:
        st.logo("assets/images/logo.png", size="large")
        st.subheader("Entrenador :material/admin_panel_settings:")
        
        #st.write(f"Usuario: {st.session_state['auth']['username']}")
        st.write(f"Hola **:blue-background[{st.session_state['auth']['username'].capitalize()}]** ")

        st.page_link("app.py", label="Inicio", icon=":material/home:")
        st.subheader("Modo :material/dashboard:")
        #
        #mode = st.radio("Modo", options=["Registro", "Respuestas", "Check-in", "RPE"], index=0)
        
        st.page_link("pages/registros.py", label="Registro", icon=":material/app_registration:")
        st.page_link("pages/respuestas.py", label="Respuestas", icon=":material/article_person:")
        st.page_link("pages/checkin.py", label="Check-in", icon=":material/lab_profile:")
        
        btnSalir = st.button("Cerrar Sesión", type="tertiary", icon=":material/logout:")

        if btnSalir:
            logout()

