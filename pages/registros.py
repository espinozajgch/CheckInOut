import streamlit as st
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import (
    checkin_form,
    checkout_form,
    preview_record,
    show_missing_file_help,
    responses_view,
    rpe_view,
    checkin_view,
    selection_header,
)

from src.schema import (
    new_base_record,
    validate_checkin
)

from src.io_files import (
    load_jugadoras,
    load_partes_json,
    append_jsonl,
    upsert_jsonl,
    get_record_for_player_day,
    get_record_for_player_day_turno,
    get_records_df,
    DATA_DIR,
)

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('Registro :red[:material/check_in_out:] ', divider=True)

menu()

# Load reference data
jug_df, jug_error = load_jugadoras()

if jug_error:
    st.error(jug_error)
    st.stop()

partes_df, partes_error = load_partes_json()

if partes_error:
    st.error(partes_error)
    st.stop()

jugadora, tipo, turno = selection_header(jug_df)

if not jugadora:
    st.info("Selecciona una jugadora para continuar.")
    st.stop()

record = new_base_record(
    id_jugadora=str(jugadora["id_jugadora"]),
    nombre_jugadora=str(jugadora["nombre_jugadora"]),
    tipo="checkIn" if tipo == "Check-in" else "checkOut",
)
record["turno"] = turno or ""

# Notice if will update existing record of today and turno
existing_today = (
    get_record_for_player_day_turno(record["id_jugadora"], record["fecha_hora"], record.get("turno", ""))
    if jugadora
    else None
)
if existing_today:
    st.info(
        "Ya existe un registro para esta jugadora hoy en el mismo turno. Al guardar se actualizará el registro existente (upsert)."
    )

is_valid = False

if tipo == "Check-in":
    record, is_valid, validation_msg = checkin_form(record, partes_df)
else:
    record, is_valid, validation_msg = checkout_form(record)

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
