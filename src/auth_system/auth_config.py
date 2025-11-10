import streamlit as st

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
