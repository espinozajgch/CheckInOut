import streamlit as st
import datetime
import pandas as pd
from src.db.db_catalogs import load_catalog_list_db
from src.schema import DIAS_SEMANA
from src.i18n.i18n import t
from src.app_config.styles import WELLNESS_COLOR_NORMAL, WELLNESS_COLOR_INVERTIDO

def checkin_form(record: dict, genero: str) -> tuple[dict, bool, str]:
    """Formulario de Check-in (Wellness pre-entrenamiento) con ICS y periodización táctica adaptativa."""

    #st.session_state.clear()
    if "dia_plus" not in st.session_state:
        st.session_state["dia_plus"] = "MD+1"  # valor por defecto

    if "dia_minor" not in st.session_state:
        st.session_state["dia_minor"] = "MD-6"  # valor por defecto

    zonas_anatomicas_df = load_catalog_list_db("zonas_anatomicas", as_df=True)
    map_zonas_anatomicas_nombre_a_id = dict(zip(zonas_anatomicas_df["nombre"], zonas_anatomicas_df["id"]))
    zonas_anatomicas_list = zonas_anatomicas_df["nombre"].tolist()

    estimulos_campo_df = load_catalog_list_db("estimulos_campo", as_df=True)
    map_estimulos_campo_nombre_a_id = dict(zip(estimulos_campo_df["nombre"], estimulos_campo_df["id"]))
    estimulos_campo_list = estimulos_campo_df["nombre"].tolist()

    estimulos_readaptacion_df = load_catalog_list_db("estimulos_readaptacion", as_df=True)
    map_estimulos_readaptacion_nombre_a_id = dict(zip(estimulos_readaptacion_df["nombre"], estimulos_readaptacion_df["id"]))
    estimulos_readaptacion_list = estimulos_readaptacion_df["nombre"].tolist()

    with st.container():
        st.markdown(t("**Check-in diario (pre-entrenamiento)**"))
        mostrar_tabla_referencia_wellness()

        # --- Variables principales ---
        c1, c2, c3, c4, c5 = st.columns(5)
        #c1, c2 = st.columns([0.8,4])
        with c1:
            record["recuperacion"] = st.number_input(t("**Recuperación** :green[:material/arrow_upward_alt:] (:red[**1**] - :green[**5**])"), min_value=1, max_value=5, step=1,
            help=t("1 = Muy mal recuperado · 5 = Totalmente recuperado"))
        with c2:
            record["fatiga"] = st.number_input(t("**Energía** :green[:material/arrow_upward_alt:] (:red[**1**] - :green[**5**])"), min_value=1, max_value=5, step=1,
            help=t("1 = Sin Energía · 5 = Energía Máxima"))
        with c3:
            record["sueno"] = st.number_input(t("**Sueño** :green[:material/arrow_upward_alt:] (:red[**1**] - :green[**5**])"), min_value=1, max_value=5, step=1,
            help=t("1 = Muy mala calidad . 5 = Excelente calidad"))
        with c4:
            record["stress"] = st.number_input(t("**Estrés** :green[:material/arrow_downward_alt:] (:green[**1**] - :red[**5**])"), min_value=1, max_value=5, step=1,
            help=t("1 = Relajado . 5 = Nivel de estrés muy alto"))
        with c5:
            record["dolor"] = st.number_input(t("**Dolor** :green[:material/arrow_downward_alt:] (:green[**1**] - :red[**5**])"), min_value=1, max_value=5, step=1,
            help=t("1 = Sin dolor . 5 = Dolor severo"))

        #with c1:
        # --- Dolor corporal ---
        if int(record.get("dolor", 0)) > 1:
            record["partes_cuerpo_dolor"] = st.multiselect(
                "Partes del cuerpo con dolor", options=zonas_anatomicas_list, placeholder="Selecciona una o varias partes del cuerpo con dolor"
            )
        else:
            record["partes_cuerpo_dolor"] = []

    st.divider()
    st.markdown(t("**Periodización táctica**"))

    # Días previos al partido (MD-14 a MD0)
    opciones_minor = [f"MD-{i}" for i in range(14, 0, -1)] + ["MD0"]

    # Días posteriores al partido (MD0 a MD+14)
    opciones_plus = ["MD0"] + [f"MD+{i}" for i in range(1, 15)]


    colA, colB, colC, colD, colE  = st.columns([1,1,1,2,2])
    with colA:
        fecha_sesion = datetime.date.today()
        dia_semana = fecha_sesion.strftime("%A")
        dia_semana_es = DIAS_SEMANA.get(dia_semana, dia_semana)
        st.text_input(t("Día de la sesión"), dia_semana_es, disabled=True)
    with colB:

        #opciones_plus = ["MD0", "MD+1", "MD+2", "MD+3", "MD+4", "MD+5", "MD+6", "MD+7"]
        dia_plus = st.selectbox(
            t("MD+"),
            options=opciones_plus,
            index=opciones_plus.index(st.session_state.get("dia_plus", 1)),
        )

        st.session_state["dia_plus"] = dia_plus 
        
    with colC:
        #opciones_minor = ["MD-7", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD0"]
        dia_minor = st.selectbox(
            "MD-",
            options=opciones_minor,
            index=opciones_minor.index(st.session_state.get("dia_minor", 1)),
        )

        st.session_state["dia_minor"] = dia_minor
    with colD:
        tipo_estimulo = st.selectbox(t("Tipos de estímulo"), estimulos_campo_list, index=0, key="select_tipo_estimulo")
        tipo_estimulo_id = map_estimulos_campo_nombre_a_id.get(tipo_estimulo)
        record["id_tipo_estimulo"] = tipo_estimulo_id
    with colE:
        disabled_selector = False
        if tipo_estimulo != "Readaptación":
            #estimulos_readaptacion = ["NO APLICA"] 
            estimulos_readaptacion_list = ["NO APLICA"]
            disabled_selector = True

        tipo_readaptacion = st.selectbox(t("Readaptación en campo"), estimulos_readaptacion_list, index=0,
        disabled=disabled_selector, key="select_tipo_readaptacion")
        tipo_readaptacion_id = map_estimulos_readaptacion_nombre_a_id.get(tipo_readaptacion)
        record["id_tipo_readaptacion"] = tipo_readaptacion_id
    
    periodizacion_tactica = dia_plus + " / " + dia_minor
    record["periodizacion_tactica"] = periodizacion_tactica
    
    if genero == "F":
        st.divider()
        record["en_periodo"] = st.checkbox(t("Te encuentras en periodo de menstruación"))
        st.caption(t("Esta información ayuda a gestionar las cargas con respecto a la fisiología femenina"))

    # --- Observación libre ---
    record["observacion"] = st.text_area(t("Observaciones"), value="")

    # --- Validación básica ---
    if record["dolor"] > 1 and not record["partes_cuerpo_dolor"]:
        return record, False, t("Selecciona al menos una parte del cuerpo con dolor.")

    is_valid, msg = validate_checkin(record)
    return record, is_valid, msg

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
            return False, t("Selecciona al menos una parte del cuerpo con dolor.")
    return True, ""

def mostrar_tabla_referencia_wellness():
    """Tabla de referencia explicativa (1-5) con colores tipo semáforo y escalas invertidas en Estrés y Dolor."""

    # --- Datos base ---
    data = {
        t("Variable"): [
            t("Recuperación"),
            t("Energía"),
            t("Sueño"),
            t("Estrés"),
            t("Dolor")
        ],
        "1": [
            t("Muy mal recuperado"),
            t("Extremadamente cansado"),
            t("Muy mala calidad / Insomnio"),
            t("Muy relajado / Positivo"),
            t("Sin dolor")
        ],
        "2": [
            t("Más fatigado de lo normal"),
            t("Fatigado"),
            t("Sueño inquieto o corto"),
            t("Relajado"),
            t("Dolor leve")
        ],
        "3": [
            t("Normal"),
            t("Normal"),
            t("Sueño aceptable"),
            t("Estrés controlado"),
            t("Molestias leves")
        ],
        "4": [
            t("Recuperado"),
            t("Ligera fatiga / Buen estado"),
            t("Buena calidad de sueño"),
            t("Alto nivel de estrés"),
            t("Dolor moderado")
        ],
        "5": [
            t("Totalmente recuperado"),
            t("Energía Máxima"),
            t("Excelente descanso"),
            t("Muy estresado / Irritable"),
            t("Dolor severo")
        ]
    }

    df_ref = pd.DataFrame(data).set_index(t("Variable"))

    # --- Función de color por celda (usando estilos globales) ---
    def color_by_col(col):
        if col.name not in ["1", "2", "3", "4", "5"]:
            return [""] * len(col)

        result = []
        for var in df_ref.index:
            # Seleccionar paleta normal o invertida según variable
            cmap = WELLNESS_COLOR_INVERTIDO if var in [t("Estrés"), t("Dolor")] else WELLNESS_COLOR_NORMAL
            color = cmap[int(col.name)]
            result.append(
                f"background-color:{color}; color:white; text-align:center; font-weight:bold;"
            )
        return result

    # --- Aplicar estilo ---
    styled_df = df_ref.style.apply(color_by_col, subset=["1", "2", "3", "4", "5"], axis=0)

    # --- Mostrar tabla en Streamlit ---
    with st.expander(t("Ver tabla de referencia de escalas (1-5)")):
        st.dataframe(styled_df, hide_index=False)
        st.caption(t(
            "**Interpretación:**\n"
            "- En **Recuperación**, **Energía** y **Sueño** -> valores altos indican bienestar.\n"
            "- En **Estrés** y **Dolor** → valores bajos indican bienestar (escala invertida).")
        )
