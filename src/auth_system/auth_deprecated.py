import streamlit as st
import jwt
import datetime
import bcrypt
from st_cookies_manager import EncryptedCookieManager
from src.db_login import load_user_from_db

# ============================
# 🔐 CONFIGURACIÓN DE SEGURIDAD
# ============================

# --- JWT ---
JWT_SECRET = st.secrets["auth"]["jwt_secret"]
JWT_ALGORITHM = st.secrets["auth"]["algorithm"]
JWT_EXP_SECONDS = int(st.secrets["auth"]["token_expiration"])  # tiempo de expiración (8h)

# --- COOKIES ---
COOKIE_SECRET = st.secrets["auth"]["cookie_secret"]
COOKIE_NAME = st.secrets["auth"]["cookie_name"]
COOKIE_EXP_DAYS = int(st.secrets["auth"]["cookie_expiration_days"])

# === Instancia global de cookies (una sola en toda la app) ===
cookies = EncryptedCookieManager(
    password=COOKIE_SECRET,  # debe ser str, no bytes
    prefix=COOKIE_NAME
)
if not cookies.ready():
    st.stop()

# ============================
# 🧩 FUNCIONES AUXILIARES
# ============================
def _ensure_str(x) -> str:
    """Convierte bytes a str si es necesario (para compatibilidad PyJWT y cookies)."""
    return x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else str(x)

# ============================
# ⚙️ ESTADO DE SESIÓN
# ============================
def ensure_session_defaults() -> None:
    """Inicializa valores por defecto en session_state."""
    if "auth" not in st.session_state:
        st.session_state["auth"] = {
            "is_logged_in": False,
            "username": "",
            "rol": "",
            "token": "",
            "cookie_key": ""
        }

def init_app_state():
    ensure_session_defaults()
    if "flash" not in st.session_state:
        st.session_state["flash"] = None

# ============================
# 🔑 JWT FUNCTIONS
# ============================
def create_jwt_token(username: str, rol: str) -> str:
    """Crea un token JWT firmado con expiración."""
    exp_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_SECONDS)
    payload = {
        "user": username,
        "rol": rol,
        "exp": exp_time,
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return _ensure_str(token)

def decode_jwt_token(token: str):
    """Valida y decodifica un token JWT, devuelve el payload o None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ============================
# 🔒 VALIDACIÓN DE LOGIN
# ============================
def validate_password(password, user):
    """Valida la contraseña y genera token + cookie única por usuario."""
    if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        token = create_jwt_token(user["email"], user["role_name"])
        token = _ensure_str(token)

        # Clave única de cookie por usuario (ej: auth_token_ana_gmail_com)
        cookie_key = f"auth_token_{user['email'].replace('@', '_').replace('.', '_')}"

        st.session_state["auth"].update({
            "is_logged_in": True,
            "username": user["email"],
            "rol": user["role_name"].lower(),
            "nombre": f"{user['name']} {user['lastname']}".strip(),
            "token": token,
            "cookie_key": cookie_key
        })

        cookies[cookie_key] = token
        cookies.save()

        st.success(":material/check: Autenticado correctamente.")
        st.rerun()
    else:
        st.error("Usuario o contraseña incorrectos")

def get_current_user():
    """Valida token desde session_state o cookie."""
    ensure_session_defaults()

    cookie_key = st.session_state["auth"].get("cookie_key")
    token = st.session_state["auth"].get("token")

    # Si no hay token en memoria, buscar cookie propia
    if not token and cookie_key:
        token = cookies.get(cookie_key)
    elif not token and not cookie_key:
        # Buscar cualquier cookie activa del formato auth_token_*
        possible_cookies = [k for k in cookies.keys() if k.startswith("auth_token_")]
        if possible_cookies:
            cookie_key = possible_cookies[0]
            token = cookies.get(cookie_key)
            st.session_state["auth"]["cookie_key"] = cookie_key

    if not token:
        return None

    token = _ensure_str(token)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        st.session_state["auth"].update({
            "is_logged_in": True,
            "username": payload["user"],
            "rol": payload["rol"],
            "token": token
        })
        return payload["user"]
    except jwt.ExpiredSignatureError:
        logout()
        return None
    except jwt.InvalidTokenError:
        logout()
        return None

def validate_login():
    """Verifica si hay sesión activa."""
    username = get_current_user()
    return bool(username)

# ============================
# 🧭 MENÚ LATERAL
# ============================
def menu():
    with st.sidebar:
        st.logo("assets/images/banner.png", size="large")
        st.subheader(f'Rol: {st.session_state["auth"]["rol"].capitalize()} :material/admin_panel_settings:')
        st.write(f"Hola **:blue-background[{st.session_state['auth']['username'].capitalize()}]** ")

        st.page_link("app.py", label="Inicio", icon=":material/home:")
        st.subheader("Modo :material/dashboard:")
        st.page_link("pages/registro.py", label="Registro", icon=":material/article_person:")
        st.subheader("Análisis y Estadísticas  :material/query_stats:")
        st.page_link("pages/individual.py", label="Individual", icon=":material/accessible_menu:")
        st.page_link("pages/grupal.py", label="Grupal", icon=":material/groups:")

        if st.session_state["auth"]["rol"].lower() in ["admin", "developer"]:
            st.subheader("Administración :material/settings:")
            st.page_link("pages/files.py", label="Registros", icon=":material/docs:")

        if st.button("Cerrar Sesión", type="tertiary", icon=":material/logout:"):
            logout()

# ============================
# 🔐 LOGIN FORM
# ============================
def login_view() -> None:
    """Renderiza el formulario de inicio de sesión."""
    _, col2, _ = st.columns([2, 1.5, 2])
    with col2:
        st.markdown("""
            <style>
                [data-testid="stSidebar"], 
                [data-testid="stBaseButton-headerNoPadding"] { display: none !important; }
            </style>
        """, unsafe_allow_html=True)

        st.image("assets/images/banner.png")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario", value="")
            password = st.text_input("Contraseña", type="password", value="")
            submitted = st.form_submit_button("Iniciar sesión", type="primary")

        if submitted:
            user_data = load_user_from_db(username)
            if not user_data:
                st.error("Usuario no encontrado o inactivo.")
                st.stop()
            validate_password(password, user_data)

# ============================
# 🚪 LOGOUT
# ============================
def logout() -> None:
    """Elimina sesión y cookie del usuario actual."""
    cookie_key = st.session_state["auth"].get("cookie_key")

    if cookie_key and cookie_key in cookies:
        cookies[cookie_key] = ""
        cookies.save()

    st.session_state["auth"] = {
        "is_logged_in": False,
        "username": "",
        "token": "",
        "rol": "",
        "cookie_key": ""
    }

    st.rerun()
