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
    load_partes_cuerpo,
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


st.header(':red[Check-In]', divider=True)

menu()

df = get_records_df()
checkin_view(df)

