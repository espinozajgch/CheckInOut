import streamlit as st
import pandas as pd
import src.config as config

# from src.io_files import (
#     load_jugadoras,
#     load_partes_cuerpo,
#     append_jsonl,
#     upsert_jsonl,
#     get_record_for_player_day,
#     get_record_for_player_day_turno,
#     get_records_df,
#     DATA_DIR,
# )

# from src.schema import (
#     new_base_record,
#     validate_checkin
# )

# from src.ui_components import (
#     checkin_form,
#     checkout_form,
#     preview_record,
#     show_missing_file_help,
#     responses_view,
#     rpe_view,
#     checkin_view,
#     selection_header,
# )

config.init_config()

from src.auth import init_app_state, login_view, menu, validate_login

init_app_state()
validate_login()

# if not cookies.ready():
#     st.stop()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('Wellness & :red[RPE]', divider=True)
menu()

# # Top bar with logout
# with st.sidebar:
#     st.logo("assets/images/logo.png", size="large")
#     st.subheader("Entrenador :material/sports:")
    
#     #st.write(f"Usuario: {st.session_state['auth']['username']}")
#     st.write(f"Hola **:blue-background[{st.session_state['auth']['username']}]** ")
#     #st.subheader("Modo :material/dashboard:")
#     #mode = st.radio("Modo", options=["Registro", "Respuestas", "Check-in", "RPE"], index=0)
#     logout_button()
#     st.page_link("pages/registros.py", label="Registro", icon=":material/sports:")
#     #st.page_link("pages/logout.py", label="Salir", icon=":material/logout:")
#     st.divider()
    

# # Show flash message if present (e.g., after saving)
# if st.session_state.get("flash"):
#     st.success(st.session_state["flash"])
#     st.session_state["flash"] = None

# # Load reference data
# jug_df, jug_error = load_jugadoras()
# partes_df, partes_error = load_partes_cuerpo()

# if jug_error:
#     show_missing_file_help(
#         title="Falta archivo de jugadoras",
#         description=jug_error,
#         template_type="jugadoras",
#     )
#     st.stop()

# if partes_error:
#     show_missing_file_help(
#         title="Falta archivo de partes del cuerpo",
#         description=partes_error,
#         template_type="partes_cuerpo",
#     )
#     st.stop()

# # Selection header
# if 'mode' not in locals():
#     mode = "Registro"

# if mode == "Respuestas":
#     df = get_records_df()
#     responses_view(df)
#     st.stop()

# if mode == "RPE":
#     df = get_records_df()
#     rpe_view(df)
#     st.stop()

# if mode == "Check-in":
#     df = get_records_df()
#     checkin_view(df)
#     st.stop()

# ##############################################################

# # Registro
# jugadora, tipo, turno = selection_header(jug_df)
# #st.divider()

# if not jugadora:
#     st.info("Selecciona una jugadora para continuar.")
#     st.stop()

# record = new_base_record(
#     id_jugadora=str(jugadora["id_jugadora"]),
#     nombre_jugadora=str(jugadora["nombre_jugadora"]),
#     tipo="checkIn" if tipo == "Check-in" else "checkOut",
# )
# record["turno"] = turno or ""

# # Notice if will update existing record of today and turno
# existing_today = (
#     get_record_for_player_day_turno(record["id_jugadora"], record["fecha_hora"], record.get("turno", ""))
#     if jugadora
#     else None
# )
# if existing_today:
#     st.info(
#         "Ya existe un registro para esta jugadora hoy en el mismo turno. Al guardar se actualizará el registro existente (upsert)."
#     )

# is_valid = False

# st.divider()

# if tipo == "Check-in":
#     record, is_valid, validation_msg = checkin_form(record, partes_df)
# else:
#     record, is_valid, validation_msg = checkout_form(record)

# if not is_valid and validation_msg:
#     st.error(validation_msg)

# # Preview and save
# st.divider()

# if st.checkbox("Previsualización"):
#     preview_record(record)
#     st.caption(f"Datos almacenados en: {DATA_DIR}/registros.jsonl")

# save_col1, save_col2 = st.columns([1, 2])
# with save_col1:
#     disabled = not is_valid
#     if disabled:
#         st.button("Guardar", disabled=True)
#     else:
#         if st.button("Guardar", type="primary"):
#             # Upsert: si ya existe un registro para la misma jugadora y día, se actualiza.
#             upsert_jsonl(record)
            
#             # Set flash message to show after rerun
#             st.session_state["flash"] = "Registro guardado/actualizado correctamente en data/registros.jsonl"
#             # Clear form state by reloading
#             st.rerun()

# # with save_col2:
# #     if not is_valid and validation_msg:
# #         st.error(validation_msg)

