import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
from src.checkin_ui import checkin_form
from src.db_records import load_jugadoras_db, load_competiciones_db
from src.check_out import checkout_form

init_app_state()

from src.ui_components import (
    preview_record,
    selection_header,
)

from src.schema import (
    new_base_record
)

from src.io_files import (
    load_partes_json, upsert_jsonl,
    get_record_for_player_day_turno, DATA_DIR,
)

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

jugadora, tipo, turno = selection_header(jug_df, comp_df)

st.divider()

if not jugadora:
    st.info("Selecciona una jugadora para continuar.")
    st.stop()

record = new_base_record(
    id_jugadora=str(jugadora["identificacion"]),
    nombre_jugadora=str(jugadora["nombre"] + " " + jugadora["apellido"]),
    tipo="checkIn" if tipo == "Check-in" else "checkOut",
)
record["turno"] = turno or ""

# Notice if will update existing record of today and turno
existing_today = (
    get_record_for_player_day_turno(record["identificacion"], record["fecha_hora"], record.get("turno", ""))
    if jugadora
    else None
)
if existing_today:
    st.info(
        "Ya existe un registro para esta jugadora hoy en el mismo turno. Al guardar se actualizará el registro existente (upsert)."
    )

is_valid = False

#st.dataframe(jugadora["sexo"])

if tipo == "Check-in":
    record, is_valid, validation_msg = checkin_form(record, jugadora["sexo"])
else:
    record, is_valid, validation_msg = checkout_form(record)

if st.session_state["auth"]["rol"].lower() == "admin":
    # Preview and save
    st.divider()

    if st.checkbox("Previsualización"):
        preview_record(record)
        st.caption(f"Datos almacenados en: {DATA_DIR}/registros.jsonl")

save_col1, save_col2 = st.columns([1, 2])
with save_col1:
    disabled = not is_valid
    if disabled:
        st.button("Guardar", disabled=True)
    else:
        if st.button("Guardar", type="primary"):
            # Upsert: si ya existe un registro para la misma jugadora y día, se actualiza.
            upsert_jsonl(record)
            # Set flash message to show after rerun
            st.session_state["flash"] = "Registro guardado/actualizado correctamente en data/registros.jsonl"
            # Clear form state by reloading
            st.rerun()


if not is_valid and validation_msg:
    st.error(validation_msg)

#st.caption(f"Datos almacenados en: {DATA_DIR}/registros.jsonl")
