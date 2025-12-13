import pandas as pd
import streamlit as st
import datetime
from util.util import get_date_range_input
from i18n.i18n import t
from schema import OPCIONES_TURNO
import json

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

    if modo == "registro":
        return jugadora_opt, tipo, turno
    
    # ==================================================
    # 🧮 FILTRADO DEL DATAFRAME
    # ==================================================
    #st.text(t("Filtrando registros..."))
    df_filtrado = filtrar_registros(
        records_df,
        jugadora_opt=jugadora_opt,
        turno=turno,
        modo=modo,
        tipo=tipo,   # solo si modo="registros"
        start=start,
        end=end,
    )

    return df_filtrado, jugadora_opt, tipo, turno, start, end

def filtrar_registros(
    records_df: pd.DataFrame,
    jugadora_opt: dict | None = None,
    turno: str = "Todos",
    modo: str = "registros",
    tipo: str | None = None,
    start=None,
    end=None,
) -> pd.DataFrame:
    """
    Filtra el DataFrame de registros según los criterios seleccionados.

    Parámetros:
        records_df: DataFrame original.
        jugadora_opt: dict con datos de la jugadora seleccionada (o None).
        turno: "Todos", "Turno 1", "Turno 2", "Turno 3".
        modo: "registros" o "reporte".
        tipo: string del tipo de registro (solo si modo="registros").
        start: fecha inicio (solo si modo="reporte").
        end: fecha fin (solo si modo="reporte").

    Retorna:
        DataFrame filtrado.
    """

    df_filtrado = records_df.copy()

    if df_filtrado.empty:
        return df_filtrado

    # -------------------------
    # Filtrar por jugadora
    # -------------------------
    if jugadora_opt:
        df_filtrado = df_filtrado[
            df_filtrado["id_jugadora"] == jugadora_opt["id_jugadora"]
        ]

    # -------------------------
    # Filtrar por turno
    # -------------------------
    if turno != "Todos":
        df_filtrado = df_filtrado[df_filtrado["turno"] == turno]

    # -------------------------
    # MODO: registros
    # -------------------------
    if modo == "registros" and tipo:
        df_filtrado = df_filtrado[
            df_filtrado["tipo"].str.lower() == tipo.lower()
        ]

    # -------------------------
    # MODO: reporte (rango de fechas)
    # -------------------------
    elif (modo == "reporte" or modo == "reporte_grupal") and start and end:

        # Normalizar tipos de fecha
        if pd.api.types.is_datetime64_any_dtype(df_filtrado["fecha_sesion"]):
            df_filtrado["fecha_sesion"] = df_filtrado["fecha_sesion"].dt.date

        # Normalizar start y end si vienen como Timestamp
        if hasattr(start, "to_pydatetime"):
            start = start.date()
        if hasattr(end, "to_pydatetime"):
            end = end.date()

        df_filtrado = df_filtrado[
            (df_filtrado["fecha_sesion"] >= start)
            & (df_filtrado["fecha_sesion"] <= end)
        ]

    # ===========================================================
    # MODO: AUSENCIAS (usa fecha_inicio y fecha_fin)
    # Detecta solapamiento de intervalos
    # ===========================================================
    elif modo == "ausencias" and start and end:

        # Comprobar columnas esperadas
        if not {"fecha_inicio", "fecha_fin"}.issubset(df_filtrado.columns):
            return df_filtrado

        # Normalizar tipos
        if pd.api.types.is_datetime64_any_dtype(df_filtrado["fecha_inicio"]):
            df_filtrado["fecha_inicio"] = df_filtrado["fecha_inicio"].dt.date
        if pd.api.types.is_datetime64_any_dtype(df_filtrado["fecha_fin"]):
            df_filtrado["fecha_fin"] = df_filtrado["fecha_fin"].dt.date

        if hasattr(start, "to_pydatetime"):
            start = start.date()
        if hasattr(end, "to_pydatetime"):
            end = end.date()

        # Regla de solapamiento:
        # inicio <= fin_filtro AND fin >= inicio_filtro
        df_filtrado = df_filtrado[
            (df_filtrado["fecha_inicio"] <= end)
            & (df_filtrado["fecha_fin"] >= start)
        ]

    return df_filtrado

def selection_header_registro(jug_df: pd.DataFrame, comp_df: pd.DataFrame, records_df: pd.DataFrame = None):

    col_tipo, col_turno, col_plantel, col_jugadora = st.columns([1.6, 1, 2, 2])

    # ==========================================
    # 1. Tipo de registro (Check-in / Check-out)
    # ==========================================
    with col_tipo:
        tipo = st.radio(
            t("Tipo de registro"),
            options=["Check-in", "Check-out"],
            horizontal=True,
            index=0
        )

        # tipo = st.selectbox(
        #     t("Tipo de registro"),
        #     ["Check-in", "Check-out", t("Aunsente")],
        #     index=0
        # )

    # ======================
    # 2. Turno seleccionado
    # ======================
    with col_turno:
        opciones = list(OPCIONES_TURNO.values())[1:]   # ← excluye la primera opción

        turno_traducido = st.selectbox(
            t("Turno"),
            opciones,
            index=0
        )
        turno = next(k for k, v in OPCIONES_TURNO.items() if v == turno_traducido)

    # ======================
    # 3. Plantel
    # ======================
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

    # ============================================================
    # 4. Jugadoras (filtrado dinámico según reglas de negocio)
    # ============================================================
    with col_jugadora:
        jug_df_filtrado = jug_df[jug_df["plantel"] == codigo_comp].copy()

        if records_df is not None and not records_df.empty:
            #st.dataframe(records_df, hide_index=True)
            # Convertir tipos a minúsculas
            records_df["tipo"] = records_df["tipo"].astype(str).str.lower()
            records_df["turno"] = records_df["turno"].astype(str).str.lower()

            hoy = datetime.date.today()
            checkins = get_checkins(records_df, turno, hoy)
            checkouts = get_checkouts(records_df, turno, hoy)

            # ======================================================
            # LÓGICA PRINCIPAL
            # ======================================================

            # ⭐ Check-in:
            # Mostrar SOLO jugadoras sin registros (ni checkin ni checkout)
            if tipo.lower() == "check-in".lower():
                jugadoras_excluir = set(checkins).union(set(checkouts))
                jug_df_filtrado = jug_df_filtrado[
                    ~jug_df_filtrado["id_jugadora"].isin(jugadoras_excluir)
                ]

            # ⭐ Check-out:
            # Mostrar SOLO jugadoras con check-in y sin check-out
            else:
                jugadoras_mostrar = set(checkins) - set(checkouts)
                jug_df_filtrado = jug_df_filtrado[
                    jug_df_filtrado["id_jugadora"].isin(jugadoras_mostrar)
                ]

        # -----------------------------
        # Selector final de jugadora
        # -----------------------------
        jugadoras_options = jug_df_filtrado.to_dict("records")

        jugadora_opt = st.selectbox(
            t("Jugadora"),
            options=jugadoras_options,
            format_func=lambda x: x["nombre_jugadora"] if isinstance(x, dict) else "",
            index=None,
            placeholder=t("Seleccione una Jugadora"),
        )

    return jugadora_opt, tipo, turno

def get_checkins(records_df, turno: str, fecha):
    """Devuelve array de id_jugadora con CHECK-IN en la fecha y turno indicados."""
    return records_df[
        (records_df["tipo"] == "checkin") &
        (records_df["turno"] == turno.lower()) &
        (records_df["fecha_sesion"] == fecha)
    ]["id_jugadora"].unique()


def get_checkouts(records_df, turno: str, fecha):
    """Devuelve array de id_jugadora con CHECK-OUT en la fecha y turno indicados."""
    return records_df[
        (records_df["tipo"] == "checkout") &
        (records_df["turno"] == turno.lower()) &
        (records_df["fecha_sesion"] == fecha)
    ]["id_jugadora"].unique()

def preview_record(record: dict) -> None:
    #st.subheader("Previsualización")
    # Header with key fields
    jug = record.get("id_jugadora", "-")
    fecha = record.get("fecha_sesion", "-")
    turno = record.get("turno", "-")
    tipo = record.get("tipo", "-")
    st.markdown(f"**Jugadora:** {jug}  |  **Fecha:** {fecha}  |  **Turno:** {turno}  |  **Tipo:** {tipo}")
    with st.expander("Ver registro JSON", expanded=True):
        st.code(json.dumps(record, ensure_ascii=False, indent=2), language="json")
