import streamlit as st
import time

from schema import new_base_record
from ui.check_in_ui import checkin_form
from ui.check_out_ui import checkout_form
from i18n.i18n import t
from ui.ui_components import preview_record
from db.db_records import upsert_wellness_record_db, get_record_for_player_day_turno_db

def wellness_form(jugadora, tipo, turno):
    """
    Encapsula toda la lógica de creación, validación y guardado de registros Wellness/RPE
    para Check-in y Check-out.

    Parámetros:
        jugadora: dict con datos de la jugadora seleccionada.
        tipo: "Check-in" o "Check-out".
        turno: turno seleccionado ("Turno 1", "Turno 2", etc.)

    Retorna:
        None (maneja toda la UI dentro).
    """

    # ---------------------------------------
    # 1. Validación inicial: ¿jugadora?
    # ---------------------------------------
    if not jugadora:
        st.info(t("Selecciona una jugadora para continuar."))
        return

    #st.divider()

    # ---------------------------------------
    # 2. Crear record base
    # ---------------------------------------
    record = new_base_record(
        id_jugadora=str(jugadora["id_jugadora"]),
        username=st.session_state["auth"]["name"].lower(),
        tipo="checkin" if tipo == "Check-in" else "checkout",
    )
    record["turno"] = turno or ""

    # ---------------------------------------
    # 3. Verificar si existe un registro previo hoy
    # ---------------------------------------
    existing_today = get_record_for_player_day_turno_db(
        record["id_jugadora"], 
        record["fecha_sesion"], 
        record.get("turno", "")
    )

    # ---------------------------------------
    # 4. Renderizado del formulario
    # ---------------------------------------
    if tipo == "Check-in":
        record, is_valid, validation_msg = checkin_form(record, jugadora["genero"])
    else:
        # Checkout necesita un check-in previo
        if not existing_today:
            st.error(t("No existe un registro de check-in previo para esta jugadora, fecha y turno."))
            st.stop()

        record, is_valid, validation_msg = checkout_form(record)

    # ---------------------------------------
    # 6. Previsualización para developers
    # ---------------------------------------
    if st.session_state["auth"]["rol"].lower() == "developer":
        st.divider()
        if st.checkbox(t("Previsualización")):
            preview_record(record)

    # ---------------------------------------
    # 7. Guardar (upsert)
    # ---------------------------------------
    submitted = st.button(
        t("Guardar"),
        #disabled=not is_valid,
        type="primary"
    )

    if submitted:
        try:
            # ---------------------------------------
            # 5. Validaciones del formulario
            # ---------------------------------------
            if not is_valid and validation_msg:
                st.error(validation_msg)
                st.stop()

            with st.spinner(t("Actualizando Registro...")):

                modo = "checkin" if tipo == "Check-in" else "checkout"

                # Upsert: inserta o actualiza si ya existe
                success = upsert_wellness_record_db(record, modo)

                if success:
                    st.success(t(":material/done_all: Registro guardado/actualizado correctamente."))
                    time.sleep(1)
                    st.session_state["target_page"] = "registro"
                    st.switch_page("pages/switch.py")
                else:
                    st.error(t(":material/warning: Error al guardar el registro."))

        except Exception as e:
            st.error(f":material/warning: {t('Error inesperado al guardar el registro:')} {e}")
