import streamlit as st
from src.db_connection import get_connection

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
            s.name AS state_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        LEFT JOIN state_user s ON u.state_id = s.id
        WHERE u.email = %s;
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
