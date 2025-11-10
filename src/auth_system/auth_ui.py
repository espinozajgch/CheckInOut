import streamlit as st
from src.db_login import load_user_from_db
from src.auth_system.auth_core import logout, validate_password

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

