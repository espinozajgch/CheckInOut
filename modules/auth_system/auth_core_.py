import datetime
import uuid

import bcrypt
import jwt
import streamlit as st
from st_cookies_manager import EncryptedCookieManager

from modules.auth_system import auth_config  # parámetros desde secrets.toml

# ============================================================
# 🔐 GESTOR GLOBAL DE COOKIES (una instancia por app)
# ============================================================
cookies = EncryptedCookieManager(
    password=auth_config.COOKIE_SECRET,   # clave de cifrado
    prefix=auth_config.COOKIE_NAME        # nombre lógico de la app (estable)
)

if not cookies.ready():
    # Sin cookies no podemos garantizar sesiones estables
    st.stop()

# ============================================================
# 🧩 HELPERS
# ============================================================
def _ensure_str(x):
    """Normaliza bytes / str a str."""
    if isinstance(x, (bytes, bytearray)):
        return x.decode("utf-8")
    return str(x)


def _auth_default_state() -> dict:
    """Estructura base del estado de autenticación."""
    return {
        "is_logged_in": False,
        "username": "",
        "rol": "",
        "nombre": "",
        "token": "",
        "cookie_key": "",
        "session_id": "",
        "issued_at": None,
        "expires_at": None,
    }


def ensure_session_defaults() -> None:
    """Garantiza que exista st.session_state['auth'] y 'flash'."""
    if "auth" not in st.session_state:
        st.session_state["auth"] = _auth_default_state()
    if "flash" not in st.session_state:
        st.session_state["flash"] = None


def init_app_state() -> None:
    """Inicializa el estado de la app (llamado al inicio en app.py)."""
    ensure_session_defaults()


# ============================================================
# 🎫 JWT: CREACIÓN Y VALIDACIÓN
# ============================================================
def create_jwt_token(username: str, rol: str, session_id: str | None = None) -> str:
    """
    Crea un JWT por sesión, NO por usuario (usa session_id).
    """
    if session_id is None:
        session_id = uuid.uuid4().hex

    now = datetime.datetime.utcnow()
    exp_time = now + datetime.timedelta(seconds=auth_config.JWT_EXP_SECONDS)

    payload = {
        "user": username,
        "rol": rol,
        "sid": session_id,                   # 🔑 identificador de sesión
        "iat": int(now.timestamp()),
        "exp": int(exp_time.timestamp()),
    }

    token = jwt.encode(
        payload,
        auth_config.JWT_SECRET,
        algorithm=auth_config.JWT_ALGORITHM,
    )
    return _ensure_str(token)


def decode_jwt_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT.
    Retorna el payload si es válido; None si está expirado o es inválido.
    """
    try:
        payload = jwt.decode(
            token,
            auth_config.JWT_SECRET,
            algorithms=[auth_config.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Sesión expirada
        st.warning(":material/history_toggle_off: Tu sesión ha expirado. Vuelve a iniciar sesión.")
        return None
    except jwt.InvalidTokenError:
        # Token manipulado o inválido
        return None
    except Exception as e:
        st.error(f":material/error: Error al validar el token de sesión: {e}")
        return None


# ============================================================
# 🧠 GESTIÓN DEL ESTADO DE AUTENTICACIÓN
# ============================================================
def _update_auth_state_from_payload(token: str, cookie_key: str, payload: dict) -> None:
    """
    Actualiza st.session_state['auth'] a partir del payload JWT.
    """
    ensure_session_defaults()
    auth_state = st.session_state["auth"]

    auth_state.update({
        "is_logged_in": True,
        "username": payload.get("user", ""),
        "rol": (payload.get("rol") or "").lower(),
        "token": token,
        "cookie_key": cookie_key,
        "session_id": payload.get("sid", ""),
        "issued_at": payload.get("iat"),
        "expires_at": payload.get("exp"),
    })


def set_auth_session(user: dict, token: str, cookie_key: str, payload: dict) -> None:
    """
    Configura la sesión de autenticación:
    - actualiza st.session_state['auth']
    - guarda la cookie de sesión
    - marca la cookie activa para auto-login futuro
    """
    nombre_completo = f"{user.get('name', '')} {user.get('lastname', '')}".strip()

    _update_auth_state_from_payload(token, cookie_key, payload)
    st.session_state["auth"]["nombre"] = nombre_completo

    # Guarda el token asociado a esta sesión concreta
    cookies[cookie_key] = token

    # Clave “maestra” para auto-login en nuevas pestañas de ESTE navegador
    cookies["active_auth_key"] = cookie_key

    cookies.save()


# ============================================================
# 🔍 OBTENER USUARIO ACTUAL DESDE SESIÓN / COOKIE
# ============================================================
def get_current_user() -> dict | None:
    """
    Devuelve el payload JWT del usuario actual si la sesión es válida.
    Usa este orden de prioridad:
      1) Token en st.session_state['auth'] (pestaña actual)
      2) cookie_key en st.session_state['auth']
      3) cookies['active_auth_key'] -> cookie de sesión activa en este navegador
    Si algo falla, NO intenta “adivinar” usuario recorriendo todas las cookies.
    """
    ensure_session_defaults()
    auth_state = st.session_state["auth"]

    token = auth_state.get("token")
    cookie_key = auth_state.get("cookie_key")

    # 1) Si ya hay token en memoria, lo validamos
    if token:
        token = _ensure_str(token)
        payload = decode_jwt_token(token)
        if not payload:
            logout()
            return None
        _update_auth_state_from_payload(token, cookie_key or "", payload)
        return payload

    # 2) Si tenemos cookie_key en el estado, usamos esa cookie
    if not token and cookie_key:
        stored = cookies.get(cookie_key)
        if stored:
            token = _ensure_str(stored)
            payload = decode_jwt_token(token)
            if not payload:
                logout()
                return None
            _update_auth_state_from_payload(token, cookie_key, payload)
            return payload

    # 3) Auto-login suave: usar la “active_auth_key” si existe
    active_key = cookies.get("active_auth_key")
    if active_key:
        cookie_key = _ensure_str(active_key)
        stored = cookies.get(cookie_key)
        if stored:
            token = _ensure_str(stored)
            payload = decode_jwt_token(token)
            if not payload:
                # Limpieza defensiva
                try:
                    cookies[cookie_key] = ""
                    cookies["active_auth_key"] = ""
                    cookies.save()
                except Exception:
                    pass
                logout()
                return None

            _update_auth_state_from_payload(token, cookie_key, payload)
            return payload

    # Ninguna sesión válida encontrada
    return None


# ============================================================
# 🚪 LOGOUT
# ============================================================
def logout() -> None:
    """
    Cierra la sesión ACTUAL:
      - borra la cookie de esa sesión
      - limpia st.session_state['auth']
      - si coincide con active_auth_key, también la limpia
    """
    #del st.session_state["id_tipo_carga"]
    #st.session_state.clear()
    ensure_session_defaults()
    auth_state = st.session_state["auth"]
    cookie_key = auth_state.get("cookie_key")

    try:
        if cookie_key and cookie_key in cookies:
            cookies[cookie_key] = ""   # borramos el valor cifrado
        # Si esta sesión era la activa, limpimos la referencia
        active_key = cookies.get("active_auth_key")
        if active_key and _ensure_str(active_key) == cookie_key:
            cookies["active_auth_key"] = ""
        cookies.save()
    except Exception:
        # No rompemos la app si hay un problema con las cookies
        pass

    st.session_state["auth"] = _auth_default_state()
    st.rerun()


# ============================================================
# ✅ VALIDACIÓN DE LOGIN (USADA DESDE app.py)
# ============================================================
def validate_login() -> bool:
    """
    Revisa si hay una sesión válida.
    No muestra mensajes; solo retorna True/False.
    """
    payload = get_current_user()
    return payload is not None


# ============================================================
# 🔑 VALIDACIÓN DE ACCESO (LOGIN FORM) DESDE auth_ui.py
# ============================================================
def validate_access(password: str, user: dict) -> None:
    """
    Valida la contraseña y, si es correcta y tiene permisos,
    crea una sesión nueva (JWT + cookie + session_state).
    """
    # 1) Comprobar contraseña
    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        st.error("Usuario o contraseña incorrectos")
        return

    # 2) Validar permiso para esta APP
    permisos = user.get("permissions", "")
    permisos_list = [p.strip() for p in permisos.split(",")] if isinstance(permisos, str) else []

    if auth_config.APP_NAME not in permisos_list:
        st.error(":material/block: Acceso denegado. No tienes permiso para usar esta aplicación.")
        st.stop()

    # 3) Crear sesión independiente por login
    #    cookie_key único por sesión → NO se mezclan sesiones entre pestañas/navegadores
    cookie_key = f"auth_session_{uuid.uuid4().hex}"

    # El session_id que irá dentro del token puede ser el mismo cookie_key
    token = create_jwt_token(user["email"], user["role_name"], session_id=cookie_key)
    token = _ensure_str(token)

    payload = decode_jwt_token(token)
    if not payload:
        st.error(":material/error: No se pudo crear la sesión. Inténtalo de nuevo.")
        return

    # 4) Guardar sesión (state + cookie)
    set_auth_session(user, token, cookie_key, payload)

    st.success(":material/check: Autenticado correctamente.")
    st.rerun()
