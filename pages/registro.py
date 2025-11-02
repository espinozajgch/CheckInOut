import streamlit as st
import time
import src.config as config

config.init_config()

from src.auth import init_app_state, login_view, menu
from src.checkin_ui import checkin_form
from src.db_records import load_jugadoras_db, load_competiciones_db, upsert_wellness_record_db, get_record_for_player_day_turno_db
from src.check_out import checkout_form

init_app_state()

from src.ui_components import preview_record, selection_header
from src.schema import new_base_record

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('Registro :red[:material/check_in_out:] ', divider=True)

menu()

# Load reference data
jug_df, jug_error = load_jugadoras_db()
comp_df, comp_error = load_competiciones_db()

if jug_error:
    st.error(jug_error)
    st.stop()

jugadora, tipo, turno, _, _ = selection_header(jug_df, comp_df)

st.divider()

if not jugadora:
    st.info("Selecciona una jugadora para continuar.")
    st.stop()

record = new_base_record(
    id_jugadora=str(jugadora["identificacion"]),
    username=st.session_state['auth']['username'],
    tipo="checkin" if tipo == "Check-in" else "checkout",
)
record["turno"] = turno or ""

# Notice if will update existing record of today and turno
existing_today = (
    get_record_for_player_day_turno_db(record["identificacion"], record["fecha_sesion"], record.get("turno", ""))
    if jugadora else None
)

if existing_today:
    st.info(
        "Ya existe un registro para esta jugadora hoy en el mismo turno. Al guardar se actualizará el registro existente (upsert)."
    )

is_valid = False

if tipo == "Check-in":
    record, is_valid, validation_msg = checkin_form(record, jugadora["sexo"])
else:
    if not existing_today:
        st.error("No existe un registro de check-in previo para esta jugadora, fecha y turno.")
        st.stop()
        
    record, is_valid, validation_msg = checkout_form(record)

if st.session_state["auth"]["rol"].lower() == "developer":
    st.divider()
    if st.checkbox("Previsualización"):
        preview_record(record)

disabled_guardar = not is_valid
submitted = st.button("Guardar",disabled=disabled_guardar, type="primary")
success = False

if submitted:
    try:
        with st.spinner("Actualizando lesión..."):
            modo = "checkin" if tipo == "Check-in" else "checkout"
            # Upsert: si ya existe un registro para la misma jugadora y día, se actualiza.
            success = upsert_wellness_record_db(record, modo)
            if success:
                st.success(":material/done_all: Registro guardado/actualizado correctamente.")
                time.sleep(4)
            else:
                st.error(":material/warning: Error al guardar el registro.")
            #st.rerun()
    except Exception as e:
        # Captura cualquier error inesperado
        st.error(f":material/warning: Error inesperado al guardar el registros: {e}")
        st.session_state.form_submitted = False

if not is_valid and validation_msg:
    st.error(validation_msg)
