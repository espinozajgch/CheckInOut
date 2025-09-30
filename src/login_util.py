import streamlit as st
from utils.data_util import get_usuarios

# Validación simple de usuario y clave con un archivo csv

def validarUsuario(usuario,clave, conn):    
    """Permite la validación de usuario y clave

    Args:
        usuario (str): usuario a validar
        clave (str): clave del usuario

    Returns:
        bool: True usuario valido, False usuario invalido
    """    
    dfusuarios = get_usuarios(conn, connector_sgs.get_data)
    #dfusuarios = pd.read_csv('usuarios.csv')
    if len(dfusuarios[(dfusuarios['USUARIO']==usuario) & (dfusuarios['CLAVE']==clave)])>0:
        return True
    else:
        return False

def generarMenu(usuario, conn):
    """Genera el menú dependiendo del usuario

    Args:
        usuario (str): usuario utilizado para generar el menú
    """        
    if 'usuario' not in st.session_state or st.session_state['usuario'] != usuario:
        return  # No generar el menú si no hay sesión válida

    with st.sidebar:
        st.logo("assets/images/marcet.png", size="large")
        # Cargamos la tabla de usuarios
        dfusuarios = get_usuarios(conn, connector_sgs.get_data)

        # Filtramos la tabla de usuarios
        dfUsuario =dfusuarios[(dfusuarios['USUARIO']==usuario)]
        # Cargamos el nombre del usuario
        nombre= dfUsuario['NOMBRE'].values[0]
        #Mostramos el nombre del usuario
        st.write(f"Hola **:blue-background[{nombre}]** ")
        # Mostramos los enlaces de páginas
        st.page_link("inicio.py", label="Inicio", icon=":material/home:")
        st.subheader("Tableros :material/dashboard:")
        st.page_link("pages/playerhub.py", label="PlayerHub", icon=":material/contacts:")
        #st.page_link('pages/teams.py', label="StatsLab", icon=":material/query_stats:")
        st.subheader("Administrador :material/manage_accounts:")
        st.page_link("pages/players.py", label="Jugadores", icon=":material/account_circle:")  
        st.page_link("pages/tests.py", label="Test Fisicos", icon=":material/directions_run:")
        st.page_link("pages/users.py", label="Usuarios", icon=":material/groups:")
        
        st.page_link("pages/logout.py", label="Salir", icon=":material/logout:")
        st.divider()
        btnReload=st.button("Recargar Datos", type="tertiary", icon=":material/update:")
        if btnReload:
            st.session_state["reload_data"] = True  # Activar recarga manual
            st.rerun()

        # Botón para cerrar la sesión
        #btnSalir=st.button("Salir", type="tertiary", icon=":material/logout:")
        #if btnSalir:
        #    cerrarSesion()

        st.sidebar.image("assets/images/logo.png", width=128, use_container_width=True)
        
def generarLogin(conn):
    """
    Muestra el formulario de login si no hay sesión activa.
    Si hay ?user= en la URL y es válido, restaura sesión.
    """

    # Paso 1: Restaurar sesión desde la URL si no hay sesión activa
    if 'usuario' not in st.session_state:
        usuario_url = st.query_params.get("user", None)
        if usuario_url:
            dfusuarios = get_usuarios(conn, connector_sgs.get_data)
            if usuario_url in dfusuarios['USUARIO'].values:
                st.session_state['usuario'] = usuario_url
                # Limpiar la URL para ocultar el ?user=... tras el login
                st.query_params.clear()
                st.rerun()

    # Paso 2: Si ya hay usuario en sesión, mostrar menú
    if 'usuario' in st.session_state:
        # Nos aseguramos de que esté también en la URL
        if st.query_params.get("user", None) != st.session_state['usuario']:
            st.query_params["user"] = st.session_state['usuario']
        generarMenu(st.session_state['usuario'], conn)

    # Paso 3: Si no hay sesión activa, mostrar formulario de login
    else:
        col1, col2, col3 = st.columns([2, 1.5, 2])
        with col2:
            st.image("assets/images/marcet.png")
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
                </style>
            """, unsafe_allow_html=True)
            
            with st.form('frmLogin'):
                parUsuario = st.text_input('Usuario')
                parPassword = st.text_input('Password', type='password')
                btnLogin = st.form_submit_button('Ingresar', type='primary')

                if btnLogin:
                    if validarUsuario(parUsuario, parPassword, conn):
                        st.session_state['usuario'] = parUsuario
                        st.query_params['user'] = parUsuario
                        st.rerun()
                    else:
                        st.error("Usuario o clave inválidos", icon=":material/gpp_maybe:")
            st.image("assets/images/logo.png")

# 🔹 Función para cerrar sesión y limpiar query_params
def cerrarSesion():
    if 'usuario' in st.session_state:
        del st.session_state['usuario']
    
    st.query_params.clear()  # 🔹 Limpia la URL
    st.session_state.clear()
    st.rerun()