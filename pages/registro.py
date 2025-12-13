#from bootstrap import *

import streamlit as st
from app_config import config
config.init_config()

from auth_system.auth_core import init_app_state, validate_login
from i18n.i18n import t
from db.db_records import (load_jugadoras_db, load_competiciones_db, 
                               get_records_db, load_ausencias_activas_db)
from db.db_catalogs import load_catalog_list_db
from ui.absents_ui import absents_form, filtrar_jugadoras_ausentes

from ui.ui_components import selection_header_registro
from ui.wellness_ui import wellness_form

# Authentication gate
init_app_state()
is_valid = validate_login()

##:red[:material/check_in_out:]
st.header(t("Registro"), divider="red")

# Load reference data
wellness_df = get_records_db()
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()

tipo_ausencia_df = load_catalog_list_db("tipo_ausencia", as_df=True)
ausencias_df = load_ausencias_activas_db()

jug_df = filtrar_jugadoras_ausentes(jug_df, ausencias_df)

tab1, tab2 = st.tabs([ "Wellness :material/check_in_out:", "Ausencias :material/event_busy:"])

with tab1:
    jugadora, tipo, turno = selection_header_registro(jug_df, comp_df, wellness_df)
    wellness_form(jugadora, tipo, turno)
with tab2:
    absents_form(comp_df, jug_df, tipo_ausencia_df, ausencias_df, wellness_df)