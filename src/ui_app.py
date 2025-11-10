import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

from src.styles import WELLNESS_COLOR_NORMAL, WELLNESS_COLOR_INVERTIDO, get_color_wellness

W_COLS = ["recuperacion", "energia", "sueno", "stress", "dolor"]

# ============================================================
# ⚙️ FUNCIONES BASE
# ============================================================

def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

def compute_player_wellness_means(df_in_period_checkin: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve por Jugadora:
      - prom_w_1_5: promedio (1-5) de las 5 variables wellness
      - dolor_mean: promedio de dolor (1-5)
      - en_riesgo: bool con la lógica consensuada
    Solo usa registros tipo 'checkin' del periodo filtrado.
    """
    if df_in_period_checkin.empty:
        return pd.DataFrame(columns=["Jugadora", "prom_w_1_5", "dolor_mean", "en_riesgo"])

    df = df_in_period_checkin.copy()
    df["Jugadora"] = (df["nombre"].fillna("") + " " + df["apellido"].fillna("")).str.strip()
    df = _coerce_numeric(df, W_COLS)

    g = df.groupby("Jugadora", as_index=False)[W_COLS].mean(numeric_only=True)
    g["prom_w_1_5"] = g[W_COLS].mean(axis=1, skipna=True)
    g["dolor_mean"] = g["dolor"]
    g["en_riesgo"] = (g["prom_w_1_5"] * 5 < 15) | (g["dolor_mean"] > 3)

    return g[["Jugadora", "prom_w_1_5", "dolor_mean", "en_riesgo"]]

# ============================================================
# 📅 GESTIÓN DE PERIODOS
# ============================================================

def get_default_period(df: pd.DataFrame) -> str:
    hoy = date.today()
    dias_disponibles = df["fecha_dia"].unique()
    if hoy in dias_disponibles:
        return "Hoy"
    elif (hoy - timedelta(days=1)) in dias_disponibles:
        return "Último día"
    elif any((hoy - timedelta(days=i)) in dias_disponibles for i in range(2, 8)):
        return "Semana"
    else:
        return "Mes"


def filter_df_by_period(df: pd.DataFrame, periodo: str):
    fecha_max = df["fecha_hora_registro"].max()
    if periodo == "Hoy":
        filtro = df["fecha_dia"] == date.today()
        texto = "el día de hoy"
    elif periodo == "Último día":
        filtro = df["fecha_dia"] == fecha_max.date()
        texto = "el último día"
    elif periodo == "Semana":
        filtro = df["fecha_hora_registro"] >= (fecha_max - pd.Timedelta(days=7))
        texto = "la última semana"
    else:
        filtro = df["fecha_hora_registro"] >= (fecha_max - pd.Timedelta(days=30))
        texto = "el último mes"
    return df[filtro], texto


# ============================================================
# 📈 FUNCIONES AUXILIARES
# ============================================================

def calc_delta(values):
    if len(values) < 2 or values[-2] == 0:
        return 0
    return round(((values[-1] - values[-2]) / values[-2]) * 100, 1)


def calc_trend(df, by_col, target_col, agg="mean"):
    if agg == "sum":
        g = df.groupby(by_col)[target_col].sum().reset_index(name="valor")
    else:
        g = df.groupby(by_col)[target_col].mean().reset_index(name="valor")
    return g.sort_values(by_col)["valor"].tolist()


def calc_metric_block(df, periodo, var, agg="mean"):
    if periodo in ["Hoy", "Último día"]:
        valor = round(df[var].mean(), 1) if agg == "mean" else int(df[var].sum())
        chart, delta = [valor], 0
    elif periodo == "Semana":
        vals = calc_trend(df, "semana", var, agg)
        valor = round(vals[-1], 1) if vals else 0
        chart, delta = vals, calc_delta(vals)
    else:
        vals = calc_trend(df, "mes", var, agg)
        valor = round(vals[-1], 1) if vals else 0
        chart, delta = vals, calc_delta(vals)
    return valor, chart, delta

def calc_alertas(df_periodo: pd.DataFrame, df_completo: pd.DataFrame, periodo: str):
    """
    Calcula el número y porcentaje de jugadoras en riesgo dentro del periodo seleccionado.

    ✔️ Compatible con el nuevo modelo donde 'checkout' sobrescribe 'checkin'.
    ✔️ Usa compute_player_wellness_means(df_periodo) para coherencia global.
    """

    if df_periodo.empty:
        return 0, 0, 0, [], 0

    # --- Si existen registros tipo 'checkin', los usamos, de lo contrario todo el periodo ---
    if "tipo" in df_periodo.columns:
        df_in = df_periodo[df_periodo["tipo"].str.lower() == "checkin"].copy()
    else:
        df_in = pd.DataFrame()

    # En el modelo actual, el checkout reemplaza el checkin → fallback a todo el periodo
    base_df = df_in if not df_in.empty else df_periodo.copy()

    # --- Calcular riesgo global coherente ---
    try:
        riesgo_df = compute_player_wellness_means(base_df)
        if riesgo_df.empty or "en_riesgo" not in riesgo_df.columns:
            alertas_count = 0
            total_jugadoras = len(base_df["id_jugadora"].unique())
        else:
            alertas_count = int(riesgo_df["en_riesgo"].sum())
            total_jugadoras = int(riesgo_df.shape[0])
    except Exception as e:
        st.warning(f"No se pudo calcular el riesgo: {e}")
        alertas_count = 0
        total_jugadoras = len(base_df["id_jugadora"].unique())

    alertas_pct = round((alertas_count / total_jugadoras) * 100, 1) if total_jugadoras > 0 else 0

    # --- Simulación de 'chart' y 'delta' para compatibilidad con render_metric_cards ---
    chart_alertas = [alertas_pct]
    delta_alertas = 0

    return alertas_count, total_jugadoras, alertas_pct, chart_alertas, delta_alertas

# ============================================================
# 💠 TARJETAS DE MÉTRICAS
# ============================================================

def render_metric_cards(wellness_prom, delta_wellness, chart_wellness, rpe_prom, delta_rpe, chart_rpe, ua_total, 
delta_ua, chart_ua, alertas_count, total_jugadoras, alertas_pct, chart_alertas, delta_alertas, articulo):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Bienestar promedio del grupo",
            f"{wellness_prom if not pd.isna(wellness_prom) else 0}/25",
            f"{delta_wellness:+.1f}%",
            chart_data=chart_wellness,
            chart_type="area",
            border=True,
            help=f"Promedio de bienestar global ({articulo})."
        )
    with col2:
        st.metric(
            "Esfuerzo percibido promedio (RPE)",
            f"{rpe_prom if not pd.isna(rpe_prom) else 0}",
            f"{delta_rpe:+.1f}%",
            chart_data=chart_rpe,
            chart_type="line",
            border=True,
            delta_color="inverse"
        )
    with col3:
        st.metric(
            "Carga interna total (UA)",
            ua_total,
            f"{delta_ua:+.1f}%",
            chart_data=chart_ua,
            chart_type="area",
            border=True
        )
    with col4:
        st.metric(
            "Jugadoras en Zona Roja",
            f"{alertas_count}/{total_jugadoras}",
            f"{delta_alertas:+.1f}%",
            chart_data=chart_alertas,
            chart_type="bar",
            border=True,
            delta_color="inverse",
            help=f"{alertas_count} de {total_jugadoras} jugadoras ({alertas_pct}%) "
                 f"con bienestar promedio <15 o dolor >3 ({articulo})."
        )

def mostrar_resumen_tecnico(wellness_prom: float, rpe_prom: float, ua_total: float,
                            alertas_count: int, total_jugadoras: int):
    """
    Muestra en pantalla el resumen técnico del grupo, con interpretación automática
    del estado de bienestar, esfuerzo percibido y riesgo de alerta.
    """

    # 🟢 Estado de bienestar (escala 25)
    estado_bienestar = (
        "óptimo" if wellness_prom > 20 else
        "moderado" if wellness_prom >= 15 else
        "en fatiga"
    )

    # 🟡 Nivel de esfuerzo percibido (RPE)
    if pd.isna(rpe_prom) or rpe_prom == 0:
        nivel_rpe = "sin datos"
    elif rpe_prom < 5:
        nivel_rpe = "bajo"
    elif rpe_prom <= 7:
        nivel_rpe = "moderado"
    else:
        nivel_rpe = "alto"

    # 🔴 Estado de alertas
    if alertas_count == 0:
        estado_alertas = "sin jugadoras en zona roja"
    elif alertas_count == 1:
        estado_alertas = "1 jugadora en seguimiento"
    else:
        estado_alertas = f"{alertas_count} jugadoras en zona roja"

    # 🧾 Resumen técnico mostrado en Streamlit
    st.markdown(
        f":material/description: **Resumen técnico:** El grupo muestra un estado de bienestar **{estado_bienestar}** "
        f"({wellness_prom}/25) con un esfuerzo percibido **{nivel_rpe}** (RPE {rpe_prom}). "
        f"La carga interna total es de **{ua_total} UA** y actualmente hay **{estado_alertas}**, "
        f"debido a que el **(promedio de bienestar x 5) < 15 puntos** (escala 25), "
        f"indicando **fatiga, sobrecarga o molestias significativas** que aumentan el riesgo de lesión o bajo rendimiento."
    )

def show_interpretation(wellness_prom, rpe_prom, ua_total, alertas_count, alertas_pct, delta_ua, total_jugadoras):
    # --- INTERPRETACIÓN VISUAL Y BRIEFING ---

    # === Generar tabla interpretativa ===
    interpretacion_data = [
        {
            "Métrica": "Índice de Bienestar Promedio",
            "Valor": f"{wellness_prom if not pd.isna(wellness_prom) else 0}/25",
            "Interpretación": (
                "🟢 Óptimo (>20): El grupo mantiene un estado físico y mental adecuado. " if wellness_prom > 20 else
                "🟡 Moderado (15-19): Existen signos leves de fatiga o estrés. " if 15 <= wellness_prom <= 19 else
                "🔴 Alerta (<15): El grupo muestra fatiga o malestar significativo. "
            )
        },
        {
            "Métrica": "RPE Promedio",
            "Valor": f"{rpe_prom if not pd.isna(rpe_prom) else 0}",
            "Interpretación": (
                "🟢 Controlado (<6): El esfuerzo percibido está dentro de los rangos esperados. " if rpe_prom < 6 else
                "🟡 Medio (6-7): Carga elevada, pero dentro de niveles aceptables. " if 6 <= rpe_prom <= 7 else
                "🔴 Alto (>7): Percepción de esfuerzo muy alta. "
            )
        },
        {
            "Métrica": "Carga Total (UA)",
            "Valor": f"{ua_total}",
            "Interpretación": (
                "🟢 Estable: La carga total se mantiene dentro de los márgenes planificados. " if abs(delta_ua) < 10 else
                "🟡 Variación moderada (10-20%): Ajustes leves de carga detectados. " if 10 <= abs(delta_ua) <= 20 else
                "🔴 Variación fuerte (>20%): Aumento o descenso brusco de la carga. "
            )
        },
        {
            "Métrica": "Jugadoras en Zona Roja",
            "Valor": f"{alertas_count}/{total_jugadoras} ({alertas_pct}%)",
            "Interpretación": (
                "🟢 Grupo estable: Ninguna jugadora muestra indicadores de riesgo. " if alertas_pct == 0 else
                "🟡 Seguimiento leve (<15%): Algunas jugadoras presentan fatiga o molestias leves. " if alertas_pct <= 15 else
                "🔴 Riesgo elevado (>15%): Varios casos de fatiga o dolor detectados. "
            )
        }
    ]

    with st.expander("Interpretación de las métricas"):
        df_interpretacion = pd.DataFrame(interpretacion_data)
        df_interpretacion["Interpretación"] = df_interpretacion["Interpretación"].str.replace("\n", "<br>")
        #st.markdown("**Interpretación de las métricas**")
        st.dataframe(df_interpretacion, hide_index=True)

        st.caption(
        "🟢 / 🔴 Los colores en los gráficos muestran *variaciones* respecto al periodo anterior "
        "(🔺 sube, 🔻 baja). Los colores en la interpretación reflejan *niveles fisiológicos* "
        "según umbrales deportivos."
    )


# ============================================================
# 📋 TABLA RESUMEN DEL PERIODO
# ============================================================

def generar_resumen_periodo(df: pd.DataFrame):
    """
    Tabla resumen del periodo (sin separar por tipo),
    manteniendo cálculo de riesgo y colores de wellness.
    """

    # --- Asegurar tipos numéricos ---
    df_periodo = df.copy()

    if df_periodo.empty:
        st.info("No hay registros disponibles en este periodo.")
        return

    # ======================================================
    # 🧱 Base y preprocesamiento
    # ======================================================
    df_periodo["Jugadora"] = (
        df_periodo["nombre"].fillna("") + " " + df_periodo["apellido"].fillna("")
    ).str.strip()

    cols_wellness = ["recuperacion", "energia", "sueno", "stress", "dolor"]

    # --- Asegurar tipos numéricos ---
    for c in cols_wellness + ["rpe", "ua"]:
        if c in df_periodo.columns:
            df_periodo[c] = pd.to_numeric(df_periodo[c], errors="coerce")

    # --- Promedios generales por jugadora ---
    resumen = (
        df_periodo.groupby("Jugadora", as_index=False)
        .agg({
            "recuperacion": "mean",
            "energia": "mean",
            "sueno": "mean",
            "stress": "mean",
            "dolor": "mean",
            "rpe": "mean",
            "ua": "mean",
        })
        .rename(columns={
            "recuperacion": "Recuperación",
            "energia": "Energía",
            "sueno": "Sueño",
            "stress": "Estrés",
            "dolor": "Dolor",
            "rpe": "RPE_promedio",
            "ua": "UA_total",
        })
        .infer_objects(copy=False)
    )


    # --- Calcular Promedio Wellness (1–5) ---
    resumen["Promedio_Wellness"] = resumen[
        ["Recuperación", "Energía", "Sueño", "Estrés", "Dolor"]
    ].mean(axis=1, skipna=True)

    # ======================================================
    # ⚠️ Cálculo de riesgo coherente con compute_player_wellness_means
    # ======================================================
    try:
        riesgo_df = compute_player_wellness_means(df_periodo)
        if "en_riesgo" in riesgo_df.columns:
            resumen = pd.merge(resumen, riesgo_df[["Jugadora", "en_riesgo"]],
                               on="Jugadora", how="left")
            resumen["En_riesgo"] = resumen["en_riesgo"].fillna(False)
            resumen.drop(columns=["en_riesgo"], inplace=True)
        else:
            resumen["En_riesgo"] = False
    except Exception as e:
        st.warning(f"No se pudo calcular el riesgo: {e}")
        resumen["En_riesgo"] = False

    resumen["En_riesgo"] = resumen["En_riesgo"].apply(lambda x: "Sí" if x else "No")

    resumen = resumen.fillna(0) 
    resumen.index = resumen.index + 1
    # ======================================================
    # 🎨 Colores y estilos
    # ======================================================
    def color_por_variable(col):
        if col.name not in ["Recuperación", "Energía", "Sueño", "Estrés", "Dolor"]:
            return [""] * len(col)
        cmap = WELLNESS_COLOR_INVERTIDO if col.name in ["Estrés", "Dolor"] else WELLNESS_COLOR_NORMAL
        return [
            f"background-color:{get_color_wellness(v, col.name)}; color:white; text-align:center; font-weight:bold;"
            if pd.notna(v) else ""
            for v in col
        ]

    def color_promedios(col):
        return [
            "background-color:#27AE60; color:white; text-align:center; font-weight:bold;" if pd.notna(v) and v >= 4 else
            "background-color:#F1C40F; color:black; text-align:center; font-weight:bold;" if pd.notna(v) and 3 <= v < 4 else
            "background-color:#E74C3C; color:white; text-align:center; font-weight:bold;" if pd.notna(v) and v < 3 else
            ""
            for v in col
        ]

    def color_rpe_ua(col):
        return [
            "background-color:#27AE60; color:white; text-align:center; font-weight:bold;" if pd.notna(v) and v < 5 else
            "background-color:#F1C40F; color:black; text-align:center; font-weight:bold;" if pd.notna(v) and 5 <= v < 7 else
            "background-color:#E74C3C; color:white; text-align:center; font-weight:bold;" if pd.notna(v) and v >= 7 else
            ""
            for v in col
        ]

    def color_riesgo(col):
        return [
            "background-color:#E53935; color:white; text-align:center; font-weight:bold;" if v == "Sí" else ""
            for v in col
        ]

    # ======================================================
    # 📊 Mostrar tabla final
    # ======================================================
    styled = (
        resumen.style
        .apply(color_por_variable, subset=["Recuperación", "Energía", "Sueño", "Estrés", "Dolor"])
        .apply(color_promedios, subset=["Promedio_Wellness"])
        .apply(color_rpe_ua, subset=["RPE_promedio"])
        .apply(color_rpe_ua, subset=["UA_total"])
        .apply(color_riesgo, subset=["En_riesgo"])
        .format(precision=2, na_rep="")
    )

    st.dataframe(styled, hide_index=True)

    st.caption(
        ":material/info: **Criterio de riesgo en la tabla:** "
        "una jugadora se considera *en riesgo* si el **promedio de bienestar (1-5x5) < 15 puntos** "
        "o si la variable **Dolor > 3**. "
        "Este criterio combina el **riesgo global** (fatiga / bienestar bajo) y el **riesgo localizado** (molestias o dolor elevado)."
    )

