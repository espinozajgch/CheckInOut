import streamlit as st
import os
import shutil
from datetime import datetime
from src.auth import ensure_session_defaults, login_view, logout_button
from src.io_files import (
    load_jugadoras,
    load_partes_cuerpo,
    append_jsonl,
    upsert_jsonl,
    get_record_for_player_day,
    get_record_for_player_day_turno,
    get_records_df,
    DATA_DIR,
)
from src.schema import (
    new_base_record,
    validate_checkin,
    validate_checkout,
)
from src.ui_components import (
    selection_header,
    checkin_form,
    checkout_form,
    preview_record,
    show_missing_file_help,
    responses_view,
    rpe_view,
    checkin_view,
    individual_report_view,
    risk_view,
)
from src.synthetic import generate_synthetic_full

# Streamlit page config
st.set_page_config(page_title="Wellness & RPE", page_icon="💪", layout="wide")


def init_app_state():
    ensure_session_defaults()
    if "flash" not in st.session_state:
        st.session_state["flash"] = None


init_app_state()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

# Top bar with logout
with st.sidebar:
    st.markdown("### Entrenador")
    st.write(f"Usuario: {st.session_state['auth']['username']}")
    logout_button()
    st.markdown("---")
    mode = st.radio("Modo", options=["Registro", "Respuestas", "Check-in", "RPE", "Riesgo", "Reporte individual"], index=0)
    with st.expander("Generar datos aleatorios (30 días)"):
        st.caption("Genera datos de Check-in y Check-out para todas las jugadoras durante 30 días. La periodización táctica avanzará de forma cronológica. Se creará un backup de data/registros.jsonl antes de escribir.")
        if st.button("Generar datos completos (30 días)"):
            try:
                summary = generate_synthetic_full(days=30, seed=777)
                backup = summary.get("backup")
                target = summary.get("target")
                ci = summary.get("created_checkin")
                co = summary.get("created_checkout")
                total = summary.get("total_upserts")
                st.session_state["flash"] = (
                    f"Datos generados: Check-in {ci}, Check-out {co}, Total upserts {total}. "
                    + (f"Backup: {backup}. " if backup else "")
                    + f"Archivo: {target}"
                )
            except Exception as e:
                st.session_state["flash"] = f"Error generando datos completos: {e}"
            st.rerun()

    with st.expander("Administrar datos"):
        st.caption("Respaldar y vaciar el archivo de registros si necesitas empezar desde cero.")
        if st.button("Vaciar registros (backup y reset)"):
            try:
                # Backup si existe
                from src.io_files import DATA_DIR, REGISTROS_JSONL
                os.makedirs(DATA_DIR, exist_ok=True)
                backup_path = None
                if os.path.exists(REGISTROS_JSONL):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = os.path.join(DATA_DIR, f"registros.backup_{ts}.jsonl")
                    shutil.copy(REGISTROS_JSONL, backup_path)
                # Vaciar archivo
                with open(REGISTROS_JSONL, "w", encoding="utf-8") as f:
                    pass
                st.session_state["flash"] = (
                    (f"Backup: {backup_path}. " if backup_path else "") + "Registros vaciados correctamente."
                )
            except Exception as e:
                st.session_state["flash"] = f"Error al vaciar registros: {e}"
            st.rerun()

st.title("Wellness & RPE")

# Show flash message if present (e.g., after saving)
if st.session_state.get("flash"):
    st.success(st.session_state["flash"])
    st.session_state["flash"] = None

# Load reference data
jug_df, jug_error = load_jugadoras()
partes_df, partes_error = load_partes_cuerpo()

if jug_error:
    show_missing_file_help(
        title="Falta archivo de jugadoras",
        description=jug_error,
        template_type="jugadoras",
    )
    st.stop()

if partes_error:
    show_missing_file_help(
        title="Falta archivo de partes del cuerpo",
        description=partes_error,
        template_type="partes_cuerpo",
    )
    st.stop()

# Selection header
if 'mode' not in locals():
    mode = "Registro"

if mode == "Respuestas":
    df = get_records_df()
    responses_view(df)
    st.stop()

if mode == "RPE":
    df = get_records_df()
    rpe_view(df)
    st.stop()

if mode == "Check-in":
    df = get_records_df()
    checkin_view(df)
    st.stop()

if mode == "Riesgo":
    df = get_records_df()
    risk_view(df)
    st.stop()

if mode == "Reporte individual":
    df = get_records_df()
    individual_report_view(df)
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
st.markdown("---")
preview_record(record)

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

with save_col2:
    if not is_valid and validation_msg:
        st.error(validation_msg)

st.caption(f"Datos almacenados en: {DATA_DIR}/registros.jsonl")
