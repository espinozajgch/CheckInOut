import streamlit as st
import src.config as config
config.init_config()
from src.util import clean_df
from src.ui_components import data_filters
from src.auth import init_app_state, login_view, menu, validate_login

init_app_state()
validate_login()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

if st.session_state["auth"]["rol"].lower() != "admin":
    st.switch_page("app.py")
    
st.header("Administrador de :red[Registros]", divider=True)

menu()

jugadora_seleccionada, posicion, records = data_filters(modo=3)

disabled = records.columns.tolist()
#df_edited = st.data_editor(records, num_rows="dynamic", disabled=disabled)
st.dataframe(records, hide_index=True)
# save_if_modified(records, df_edited)
csv_data = records.to_csv(index=False).encode("utf-8")

st.download_button(
        label="Descargar registros en CSV",
        data=csv_data,
        file_name="registros_lesiones.csv",
        mime="text/csv"
    )

if st.session_state["auth"]["rol"].lower() == "developer":
    # Convertir a JSON (texto legible, sin índices)
    json_data = records.to_json(orient="records", force_ascii=False, indent=2)
    json_bytes = json_data.encode("utf-8")

    # Botón de descarga
    st.download_button(
        label="📥 Descargar registros en JSON",
        data=json_bytes,
        file_name="registros_lesiones.json",
        mime="application/json"
    )