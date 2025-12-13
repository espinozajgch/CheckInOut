import streamlit as st
import bcrypt

# ============================
#    INIT CONFIG & AUTH
# ============================

from i18n.i18n import t
from auth_system.auth_core import init_app_state, validate_login
import app_config.config as config

config.init_config()
init_app_state()
is_valid = validate_login()

# Acceso solo para admin / developer
if st.session_state["auth"]["rol"].lower() not in ["developer"]:
    st.switch_page("app.py")

# ============================
#   PASSWORD MANAGER PAGE
# ============================

st.header(t(":red[Gestor de Contraseñas]"), divider="red")
st.markdown("Herramienta para generar contraseñas encriptadas con **bcrypt**.")

# ============================
#   FUNCIONES DE SEGURIDAD
# ============================

def hash_password(password: str) -> str:
    """
    Recibe una contraseña en texto plano y retorna el hash seguro en Bcrypt.
    """
    if isinstance(password, str):
        password = password.encode("utf-8")

    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verifica si un password coincide con su hash.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ============================
#   UI DEL GESTOR
# ============================

st.subheader("🔑 Generar Password Encriptado (bcrypt)")

password_input = st.text_input("Introduce la contraseña:", type="password")
generate_btn = st.button("Generar Hash", type="primary")

if generate_btn:
    if not password_input:
        st.warning("⚠️ Debes escribir una contraseña primero.")
    else:
        hashed = hash_password(password_input)

        st.success("Contraseña encriptada correctamente:")
        st.code(hashed, language="text")

        st.info("💡 Copia este hash y úsalo en tu base de datos.")
