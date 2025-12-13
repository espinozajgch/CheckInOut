import pandas as pd
import streamlit as st
from db.db_connection import get_connection

#@st.cache_data(ttl=3600) 
def load_user_from_db(email: str):
    """
    Obtiene un usuario desde la base de datos según su email.
    Retorna un dict con los datos del usuario o None si no existe.
    """
    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo conectar a la base de datos.")
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT 
            u.id,
            u.email,
            u.password_hash,
            u.name,
            u.lastname,
            r.name AS role_name,
            s.name AS state_name,
            GROUP_CONCAT(p.name ORDER BY p.name SEPARATOR ', ') AS permissions
        FROM users u
        INNER JOIN roles r ON u.role_id = r.id
        INNER JOIN role_permissions rp ON r.id = rp.role_id
        INNER JOIN permissions p ON rp.permission_id = p.id
        INNER JOIN state_user s ON u.state_id = s.id
        WHERE u.email = %s
        GROUP BY 
            u.id, u.email, u.password_hash, u.name, u.lastname, r.name, s.name;
        """
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        return user

    except Exception as e:
        st.error(f":material/warning: Error al obtener usuario: {e}")
        return None
    finally:
        if conn:
            conn.close()

@st.cache_data(ttl=3600) 
def load_all_users_from_db():
    """
    Obtiene todos los usuarios desde la base de datos con sus roles, estados y permisos.
    Retorna un DataFrame con la información o None si ocurre un error.
    """
    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo conectar a la base de datos.")
        return None

    try:
        query = """
        SELECT 
            u.id,
            u.email,
            u.password_hash,
            u.name,
            u.lastname,
            r.name AS role_name,
            s.name AS state_name,
            GROUP_CONCAT(p.name ORDER BY p.name SEPARATOR ', ') AS permissions
        FROM users u
        INNER JOIN roles r ON u.role_id = r.id
        INNER JOIN role_permissions rp ON r.id = rp.role_id
        INNER JOIN permissions p ON rp.permission_id = p.id
        INNER JOIN state_user s ON u.state_id = s.id
        GROUP BY 
            u.id, u.email, u.password_hash, u.name, u.lastname, r.name, s.name
        ORDER BY 
            u.name, u.lastname;
        """

        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()

        # Convertir resultados a DataFrame
        df = pd.DataFrame(rows)

        return df

    except Exception as e:
        st.error(f":material/warning: Error al cargar usuarios: {e}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
