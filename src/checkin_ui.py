from gc import disable
import streamlit as st
from .periodizacion import (tactical_periodization_block, periodizacion_por_dia, 
periodizacion_doble, periodizacion_selector, periodizacion_teorica,
mostrar_tabla_periodizacion, mostrar_tabla_referencia_wellness)
from .db_catalogs import load_catalog_list_db
from .schema import PERIODIZACION
import datetime

def checkin_form(record: dict, sexo: str) -> tuple[dict, bool, str]:
    """Formulario de Check-in (Wellness pre-entrenamiento) con ICS y periodización táctica adaptativa."""
    

    zonas_anatomicas_df = load_catalog_list_db("zonas_anatomicas", as_df=True)
    map_zonas_anatomicas_nombre_a_id = dict(zip(zonas_anatomicas_df["nombre"], zonas_anatomicas_df["id"]))
    zonas_anatomicas_list = zonas_anatomicas_df["nombre"].tolist()

    with st.container():
        st.markdown("**Check-in diario (pre-entrenamiento)**")

        # --- Variables principales ---
        c1, c2, c3, c4, c5 = st.columns(5)
        #c1, c2 = st.columns([0.8,4])
        with c1:
            record["recuperacion"] = st.number_input("**Recuperación** :green[:material/arrow_upward_alt:] (:red[**1**] - :green[**5**])", min_value=1, max_value=5, step=1,
            help="1 = Muy mal recuperado · 5 = Totalmente recuperado")
        with c2:
            record["fatiga"] = st.number_input("**Energia** :green[:material/arrow_upward_alt:] (:red[**1**] - :green[**5**])", min_value=1, max_value=5, step=1,
            help="1 = Sin Energía · 5 = Energía Máxima")
        with c3:
            record["sueno"] = st.number_input("**Sueño** :green[:material/arrow_upward_alt:] (:red[**1**] - :green[**5**])", min_value=1, max_value=5, step=1,
            help="1 = Muy mala calidad . 5 = Excelente calidad")
        with c4:
            record["stress"] = st.number_input("**Estrés** :green[:material/arrow_downward_alt:] (:green[**1**] - :red[**5**])", min_value=1, max_value=5, step=1,
            help="1 = Relajado . 5 = Nivel de estrés muy alto")
        with c5:
            record["dolor"] = st.number_input("**Dolor** :green[:material/arrow_downward_alt:] (:green[**1**] - :red[**5**])", min_value=1, max_value=5, step=1,
            help="1 = Sin dolor . 5 = Dolor severo")

        #with c1:
        # --- Dolor corporal ---
        if int(record.get("dolor", 0)) > 1:
            record["partes_cuerpo_dolor"] = st.multiselect(
                "Partes del cuerpo con dolor", options=zonas_anatomicas_list, placeholder="Selecciona una o varias partes del cuerpo con dolor"
            )
        else:
            record["partes_cuerpo_dolor"] = []

        mostrar_tabla_referencia_wellness()

    st.divider()
    st.markdown("**Periodización táctica**")

    estimulos_campo = [
        "Carga alta",
        "Carga media",
        "Carga baja",
        "Regenerativo",
        "Readaptación",
        "Coadyuvante",
        "Compensatorio",
        "Retorno de selección",
        "ABP ofensivo/defensivo",
        "Técnico-táctico controlado",
        "Potencia aeróbica específica (HIIT)",
        "Resistencia específica con balón",
        "Activación neuromuscular",
        "Recuperación activa con balón",
        "No titulares / no convocadas",
        "Aclimatación (clima/superficie)",
        "Táctico por líneas (defensa/medio/ataque)"
    ]

    estimulos_readaptacion = [
        "Aeróbica en campo",
        "Técnica sin contacto",
        "Neuromuscular (técnica de carrera, aceleraciones controladas)",
        "Intermitente en campo (p. ej., 15”/15”)",
        "Con balón (pases, conducciones)",
        "Cambios de dirección (básico)",
        "Salto/aterrizaje (bajo impacto)",
        "Golpeo progresivo",
        "Contacto progresivo",
        "Retorno parcial al grupo en campo",
        "Control post-alta en campo"
    ]


    colA, colB, colC, colD, colE  = st.columns([1,1,1,2,2])
    with colA:
        fecha_sesion = st.date_input("Fecha de la sesión", datetime.date.today(), disabled=True)
    with colB:
        dia_plus = st.selectbox(
            "MD+",
            options=["MD+6", "MD+5", "MD+4", "MD+3", "MD+2", "MD+1", "MD0"],
        )
        
    with colC:
        dia_minor = st.selectbox(
            "MD-",
            options=["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD0"],
            index=3,  # por defecto MD-3
        )
    with colD:
        tipo = st.selectbox("Tipos de estímulo", estimulos_campo, index=0, key="select_tipo_doble_")
    with colE:
        disabled_selector = False
        if tipo != "Readaptación":
            estimulos_readaptacion = ["NO APLICA"] 
            disabled_selector = True

        tipo = st.selectbox("Readaptación en campo", estimulos_readaptacion, index=0,
        disabled=disabled_selector, key="select_tipo_doble__")
    #mostrar_tabla_periodizacion()

    if sexo == "F":
        st.divider()
        record["en_periodo"] = st.checkbox("Te encuentras en periodo de mestruación")
        st.caption("Esta información ayuda a gestionar las cargas con respecto a la fisiología femenina")

    # --- Observación libre ---
    record["observacion"] = st.text_area("Observaciones", value="")


    # --- Validación básica ---
    if record["dolor"] > 1 and not record["partes_cuerpo_dolor"]:
        return record, False, "Selecciona al menos una parte del cuerpo con dolor."
    return record, True, ""

def validate_checkin(record: dict) -> tuple[bool, str]:
    # Required 1..5
    for field in ["recuperacion", "fatiga", "sueno", "stress", "dolor"]:
        value = record.get(field)
        if value is None:
            return False, f"Completa el campo '{field}'."
        if not (1 <= int(value) <= 5):
            return False, f"El campo '{field}' debe estar entre 1 y 5."
    # Dolor parts if dolor > 1
    if int(record.get("dolor", 0)) > 1:
        if not record.get("partes_cuerpo_dolor"):
            return False, "Selecciona al menos una parte del cuerpo con dolor."
    return True, ""

#essential_checkout_fields = ("minutos_sesion", "rpe")

