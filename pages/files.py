import streamlit as st
import src.config as config
config.init_config()

from src.ui_components import selection_header

from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu

from src.db_records import delete_wellness, load_jugadoras_db, load_competiciones_db, get_records_wellness_db

init_app_state()
validate_login()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

if st.session_state["auth"]["rol"].lower() not in ["admin", "developer"]:
    st.switch_page("app.py")
    
st.header("Administrador de :red[registros]", divider=True)

menu()

# Load reference data
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()

wellness_df = get_records_wellness_db()

records, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, wellness_df, modo="reporte")

if records.empty:
    st.error("No se encontraron registros")
    st.stop()

disabled = records.columns.tolist()

# --- Agregar columna de selección si no existe ---
if "seleccionar" not in records.columns:
    records.insert(0, "seleccionar", False)

#records_vista = records.drop("id", axis=1)

df_edited = st.data_editor(records, 
        column_config={
            "seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False)},   
        num_rows="fixed", hide_index=True, disabled=disabled)

ids_seleccionados = df_edited.loc[df_edited["seleccionar"], "id"].tolist()

if st.session_state["auth"]["rol"].lower() in ["developer"]:
    st.write("🩺 Registros seleccionadas:", ids_seleccionados)

#st.dataframe(records, hide_index=True)
# save_if_modified(records, df_edited)
csv_data = records.to_csv(index=False).encode("utf-8")

exito, mensaje = False, ""
# ===============================
# 🔸 Diálogo de confirmación
# ===============================
@st.dialog("Confirmar eliminación", width="small")
def dialog_eliminar():
    st.warning(f"¿Está seguro de eliminar {len(ids_seleccionados)} elemento(s)?")

    _, col2, col3 = st.columns([1.8, 1, 1])
    with col2:
        if st.button(":material/cancel: Cancelar"):
            st.rerun()
    with col3:
        if st.button(":material/delete: Eliminar", type="primary"):
            exito, mensaje = delete_wellness(ids_seleccionados)

            if exito:
                # Marcar para recarga
                st.session_state["reload_flag"] = True

            st.rerun()

if st.session_state.get("reload_flag") and exito:     
    st.success(mensaje)
    st.session_state["reload_flag"] = False

col1, col2, col3, _, _ = st.columns([1.6, 1.8, 2, 1, 1])
with col1:
    # --- Botón principal para abrir el diálogo ---
    if st.button(":material/delete: Eliminar seleccionados", disabled=len(ids_seleccionados) == 0):
        dialog_eliminar()
with col2:
    st.download_button(
            label=":material/download: Descargar registros en CSV",
            data=csv_data, file_name="registros_wellness.csv", mime="text/csv")

if st.session_state["auth"]["rol"].lower() in ["developer"]:
    with col3:
            # Convertir a JSON (texto legible, sin índices)
            json_data = records.to_json(orient="records", force_ascii=False, indent=2)
            json_bytes = json_data.encode("utf-8")

            # Botón de descarga
            st.download_button(
                label=":material/download: Descargar registros en JSON",
                data=json_bytes, file_name="registros_wellness.json", mime="application/json"
            )