import streamlit as st
import jwt, datetime, bcrypt
from st_cookies_manager import EncryptedCookieManager
from src.auth_system import config  # importa los parámetros

# --- Instancia global de cookies (única en cada app) ---
cookies = EncryptedCookieManager(
    password=config.COOKIE_SECRET,
    prefix=config.COOKIE_NAME
)
if not cookies.ready():
    st.stop()

# --- Helpers ---
def _ensure_str(x):
    return x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else str(x)

def ensure_session_defaults():
    if "auth" not in st.session_state:
        st.session_state["auth"] = {
            "is_logged_in": False, "username": "", "rol": "",
            "token": "", "cookie_key": ""
        }

def init_app_state():
    ensure_session_defaults()
    if "flash" not in st.session_state:
        st.session_state["flash"] = None

# --- JWT ---
def create_jwt_token(username, rol):
    exp_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=config.JWT_EXP_SECONDS)
    payload = {"user": username, "rol": rol, "exp": exp_time, "iat": datetime.datetime.utcnow()}
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return _ensure_str(token)

def decode_jwt_token(token):
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# --- Login helpers ---
def set_auth_session(user, token):
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

def get_current_user():
    ensure_session_defaults()
    cookie_key = st.session_state["auth"].get("cookie_key")
    token = st.session_state["auth"].get("token")

    if not token and cookie_key:
        token = cookies.get(cookie_key)
    elif not token:
        possible = [k for k in cookies.keys() if k.startswith("auth_token_")]
        if possible:
            cookie_key = possible[0]
            token = cookies.get(cookie_key)
            st.session_state["auth"]["cookie_key"] = cookie_key

    if not token:
        return None

    token = _ensure_str(token)
    payload = decode_jwt_token(token)
    if not payload:
        logout()
        return None

    st.session_state["auth"].update({
        "is_logged_in": True,
        "username": payload["user"],
        "rol": payload["rol"],
        "token": token
    })
    return payload["user"]

def logout():
    cookie_key = st.session_state["auth"].get("cookie_key")
    if cookie_key and cookie_key in cookies:
        cookies[cookie_key] = ""
        cookies.save()
    st.session_state["auth"] = {"is_logged_in": False, "username": "", "token": "", "rol": "", "cookie_key": ""}
    st.rerun()

def validate_login():
    return bool(get_current_user())

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
