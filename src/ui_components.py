import pandas as pd
import streamlit as st
import datetime
from src.util import get_date_range_input
from src.i18n.i18n import t
from src.schema import OPCIONES_TURNO

def selection_header(jug_df: pd.DataFrame, comp_df: pd.DataFrame, records_df: pd.DataFrame = None, modo: str = "registro") -> pd.DataFrame:
    """
    Muestra los filtros principales (Competición, Jugadora, Turno, Tipo/Fechas)
    y retorna el DataFrame de registros filtrado según las selecciones.
    """

    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 2])

    # --- Selección de competición ---
    with col1:
        competiciones_options = comp_df.to_dict("records")
        competicion = st.selectbox(
            t("Plantel"),
            options=competiciones_options,
            format_func=lambda x: f'{x["nombre"]} ({x["codigo"]})',
            index=3,
        )
        #st.session_state["competicion"] = competiciones_options.index(competicion)

    # --- Selección de jugadora ---
    with col2:
        jugadora_opt = None
        disabled_jugadores = True if modo == "reporte_grupal" else False
        if not jug_df.empty:
            codigo_comp = competicion["codigo"]
            jug_df_filtrado = jug_df[jug_df["plantel"] == codigo_comp]
            jugadoras_options = jug_df_filtrado.to_dict("records")

            jugadora_opt = st.selectbox(
                t("Jugadora"),
                options=jugadoras_options,
                format_func=lambda x: x["nombre_jugadora"] if isinstance(x, dict) else "",
                index=None,
                placeholder=t("Seleccione una Jugadora"),
                disabled = disabled_jugadores
            )

            #st.session_state["jugadora_opt"] = jugadora_opt["id_jugadora"] if jugadora_opt else None
        else:
            st.warning(":material/warning: No hay jugadoras cargadas para esta competición.")

    # --- Selección de turno ---
    with col3:
        turno_traducido = st.selectbox(
            t("Turno"),
            list(OPCIONES_TURNO.values()),
            index=0
        )
        turno = next(k for k, v in OPCIONES_TURNO.items() if v == turno_traducido)
        #st.session_state.get("turno_idx", 0)
        #st.session_state["turno_idx"] = ["Turno 1", "Turno 2", "Turno 3"].index(turno)

    # --- Tipo o rango de fechas según modo ---
    tipo, start, end = None, None, None
    with col4:
        if modo == "registro":
            tipo = st.radio(
                t("Tipo de registro"),
                options=["Check-in", "Check-out"], horizontal=True,
                index=0 
            )
            #if st.session_state.get("tipo") is None else ["Check-in", "Check-out"].index(st.session_state["tipo"])
            #st.session_state["tipo"] = tipo

        else:  # modo == "reporte"
            hoy = datetime.date.today()
            hace_15_dias = hoy - datetime.timedelta(days=15)

            start_default = hace_15_dias 
            end_default = hoy

            start, end = get_date_range_input(t("Rango de fechas"), start_default=start_default, end_default=end_default)

            #default_rango = st.session_state.get("fecha_rango", (hace_15_dias, hoy))
            #start, end = st.date_input( "Rango de fechas", value=(start_default, end_default), max_value=hoy )
            #st.session_state["fecha_rango"] = (start, end)

    if modo == "registro":
        return jugadora_opt, tipo, turno
    
    # ==================================================
    # 🧮 FILTRADO DEL DATAFRAME
    # ==================================================
    df_filtrado = records_df.copy()
    if not df_filtrado.empty:
        # Filtrar por competición (plantel)
        #if competicion and "codigo" in competicion:
        #    df_filtrado = df_filtrado[df_filtrado["plantel"] == competicion["codigo"]]

        # Filtrar por jugadora seleccionada
        if jugadora_opt:
            df_filtrado = df_filtrado[df_filtrado["id_jugadora"] == jugadora_opt["id_jugadora"]]

        # Filtrar por turno
        if turno:
            df_filtrado = df_filtrado[df_filtrado["turno"] == turno]

        # Filtrar por tipo o fechas
        if modo == "registros" and tipo:
            df_filtrado = df_filtrado[df_filtrado["tipo"].str.lower() == tipo.lower()]
        elif modo == "reporte" and start and end:
            # Asegurar que fecha_sesion y start/end sean del mismo tipo (date)
            if pd.api.types.is_datetime64_any_dtype(df_filtrado["fecha_sesion"]):
                df_filtrado["fecha_sesion"] = df_filtrado["fecha_sesion"].dt.date
            if hasattr(start, "to_pydatetime"):
                start = start.date()
            if hasattr(end, "to_pydatetime"):
                end = end.date()
            df_filtrado = df_filtrado[
                (df_filtrado["fecha_sesion"] >= start) & (df_filtrado["fecha_sesion"] <= end)
            ]
    
        # print(df_filtrado["fecha_sesion"].head())
        # print(df_filtrado["fecha_sesion"].dtype)
        # print(type(df_filtrado["fecha_sesion"].iloc[0]))

    return df_filtrado, jugadora_opt, tipo, turno, start, end

def selection_header_registro(jug_df: pd.DataFrame,comp_df: pd.DataFrame,records_df: pd.DataFrame = None):

    col_tipo, col_turno, col_plantel, col_jugadora = st.columns([1.5, 1, 2, 2])

    with col_tipo:
        tipo = st.radio(t("Tipo de registro"), options=["Check-in", "Check-out"], horizontal=True, index=0)
    with col_turno:
        turno_traducido = st.selectbox(
            t("Turno"),
            list(OPCIONES_TURNO.values()),
            index=0
        )
        turno = next(k for k, v in OPCIONES_TURNO.items() if v == turno_traducido)

    with col_plantel:
        comp_options = comp_df.to_dict("records")
        comp_select = st.selectbox(
            t("Plantel"),
            options=comp_options,
            format_func=lambda x: x["nombre"] if isinstance(x, dict) else "",
            index=3,
            placeholder=t("Seleccione un plantel"),
        )
        codigo_comp = comp_select["codigo"]

    with col_jugadora:
        jug_df_filtrado = jug_df[jug_df["plantel"] == codigo_comp].copy()

        if records_df is not None and not records_df.empty:
            # Asegurar tipo string en tipo y turno
            records_df["tipo"] = records_df["tipo"].astype(str).str.lower()
            records_df["turno"] = records_df["turno"].astype(str).str.lower()

            #st.text(tipo.lower())
            # Filtrar registros existentes del tipo y turno seleccionados
            registros_filtrados = records_df[
                (records_df["tipo"] == tipo.lower().replace("-", "")) &
                (records_df["turno"] == turno.lower())
            ]

            # Jugadoras con registro de este tipo y turno
            jugadoras_con_registro = registros_filtrados["id_jugadora"].unique()

            # Excluirlas del selector
            jug_df_filtrado = jug_df_filtrado[
                ~jug_df_filtrado["id_jugadora"].isin(jugadoras_con_registro)
            ]

        jugadoras_options = jug_df_filtrado.to_dict("records")

        jugadora_opt = st.selectbox(
            t("Jugadora"),
            options=jugadoras_options,
            format_func=lambda x: x["nombre_jugadora"] if isinstance(x, dict) else "",
            index=None,
            placeholder=t("Seleccione una Jugadora"),
        )
        
    return jugadora_opt, tipo, turno

def preview_record(record: dict) -> None:
    #st.subheader("Previsualización")
    # Header with key fields
    jug = record.get("id_jugadora", "-")
    fecha = record.get("fecha_sesion", "-")
    turno = record.get("turno", "-")
    tipo = record.get("tipo", "-")
    st.markdown(f"**Jugadora:** {jug}  |  **Fecha:** {fecha}  |  **Turno:** {turno}  |  **Tipo:** {tipo}")
    with st.expander("Ver registro JSON", expanded=True):
        import json

        st.code(json.dumps(record, ensure_ascii=False, indent=2), language="json")
