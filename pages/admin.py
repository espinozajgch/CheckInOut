import streamlit as st
import json
import random
import datetime
from pathlib import Path
import pandas as pd

import src.config as config
config.init_config()

from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu

#from src.auth import init_app_state, login_view, menu, validate_login
from src.io_files import load_jugadoras
from src.synthetic import generate_synthetic_full

init_app_state()
validate_login()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header("Simulador de :red[Registros]", divider="red")

menu()

col1, col2 = st.columns(2)
with col1:
    days = st.number_input("Número de días a generar", min_value=1, max_value=30, value=10, step=1)
with col2:
    seed = st.number_input("Semilla aleatoria (seed)", min_value=0, value=42, step=1)

# --- Botón principal ---
if st.button("Generar registros aleatorios", type="primary"):
    try:
        result = generate_synthetic_full(days=days, seed=seed)
        tipo = "Completo (check-in y check-out)"

        st.success(f"✅ Generación de registros {tipo} completada con éxito.")

        # Mostrar resumen
        st.markdown("### Resumen de generación")
        col1, col2, col3 = st.columns(3)
        col1.metric("Días simulados", result.get("days", 0))
        col2.metric("Registros creados", result.get("created", result.get("total_upserts", 0)))
        col3.metric("Backups generados", "✅" if result.get("backup") else "—")

        st.write("**Archivo destino:**", result.get("target", "N/D"))
        if result.get("backup"):
            st.info(f"Backup guardado en: `{result['backup']}`")

    except Exception as e:
        st.error(f"❌ Error al generar registros: {e}")


data, error = load_jugadoras()
#df = pd.DataFrame(data)
#st.dataframe(df)
