import streamlit as st
import time
import src.config as config

config.init_config()

from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu
from src.i18n.i18n import t
from src.checkin_ui import checkin_form
from src.db_records import load_jugadoras_db, load_competiciones_db, upsert_wellness_record_db, get_record_for_player_day_turno_db, get_records_wellness_db
from src.check_out import checkout_form

init_app_state()
validate_login()

from src.ui_components import preview_record, selection_header_registro
from src.schema import new_base_record

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header(t("Registro :red[:material/check_in_out:]"), divider="red")

menu()

# Load reference data
df = get_records_wellness_db()
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()

jugadora, tipo, turno = selection_header_registro(jug_df, comp_df, df)

if not jugadora:
    st.info(t("Selecciona una jugadora para continuar."))
    st.stop()

st.divider()

record = new_base_record(
    id_jugadora=str(jugadora["id_jugadora"]),
    username=st.session_state['auth']['username'],
    tipo="checkin" if tipo == "Check-in" else "checkout",
)
record["turno"] = turno or ""

# Notice if will update existing record of today and turno
existing_today = (
    get_record_for_player_day_turno_db(record["id_jugadora"], record["fecha_sesion"], record.get("turno", ""))
    if jugadora else None
)

if existing_today:
    st.info(t("Ya existe un registro para esta jugadora hoy en el mismo turno. Al guardar se actualizará el registro existente (upsert)."))

is_valid = False

if tipo == "Check-in":
    record, is_valid, validation_msg = checkin_form(record, jugadora["genero"])
else:
    if not existing_today:
        st.error(t("No existe un registro de check-in previo para esta jugadora, fecha y turno."))
        st.stop()
        
    record, is_valid, validation_msg = checkout_form(record)

if not is_valid and validation_msg:
    st.error(validation_msg)
    st.stop()

if st.session_state["auth"]["rol"].lower() == "developer":
    st.divider()
    if st.checkbox(t("Previsualización")):
        preview_record(record)

disabled_guardar = not is_valid
submitted = st.button(t("Guardar"),disabled=disabled_guardar, type="primary")
success = False

if submitted:
    try:
        with st.spinner(t("Actualizando lesión...")):
            modo = "checkin" if tipo == "Check-in" else "checkout"
            # Upsert: si ya existe un registro para la misma jugadora y día, se actualiza.
            success = upsert_wellness_record_db(record, modo)
            if success:
                st.success(t(":material/done_all: Registro guardado/actualizado correctamente."))
                time.sleep(4)
                st.rerun()
            else:
                st.error(t(":material/warning: Error al guardar el registro."))
            
    except Exception as e:
        # Captura cualquier error inesperado
        st.error(f":material/warning: {t('Error inesperado al guardar el registro:')} {e}")
        st.session_state.form_submitted = False

