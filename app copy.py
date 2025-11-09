import streamlit as st
from src.db_records import get_records_wellness_db

import src.config as config
config.init_config()
import pandas as pd

from src.auth import init_app_state, login_view, menu, validate_login
init_app_state()

from src.util import show_interpretation, clean_df

validate_login()

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header("Resumen de :red[Wellness]", divider="red")
menu()

df = get_records_wellness_db()


# --- MÉTRICAS INICIALES WELLNESS ---
if df.empty:
    st.warning("No hay registros de Wellness o RPE disponibles.")
    st.stop()

# Crear wellness_score antes de filtrar
df["wellness_score"] = df[["recuperacion", "energia", "sueno", "stress", "dolor"]].sum(axis=1)

# Selector de periodo
periodo = st.radio(
    "Tendencias:",
    ["Último día", "Semana", "Mes"],
    horizontal=True,
    index=2  # "Último día" por defecto
)

# --- Filtrado por periodo seleccionado ---
if periodo == "Último día":
    fecha_max = df["fecha_hora_registro"].max().date()
    df_periodo = df[df["fecha_hora_registro"] == fecha_max]
    articulo = "el último día"
elif periodo == "Semana":
    fecha_max = df["fecha_hora_registro"].max()
    df_periodo = df[df["fecha_hora_registro"] >= (fecha_max - pd.Timedelta(days=7))]
    articulo = "la última semana"
else:  # Mes
    fecha_max = df["fecha_hora_registro"].max()
    df_periodo = df[df["fecha_hora_registro"] >= (fecha_max - pd.Timedelta(days=30))]
    articulo = "el último mes"

# --- Agrupar según periodo (para mini-gráficos) ---
df["semana"] = df["fecha_hora_registro"].dt.isocalendar().week
df["mes"] = df["fecha_hora_registro"].dt.month
df["dia"] = df["fecha_hora_registro"].dt.date

# --- FUNCIONES AUXILIARES ---
def calc_delta(values):
    if len(values) < 2 or values[-2] == 0:
        return 0
    return round(((values[-1] - values[-2]) / values[-2]) * 100, 1)

def group_trend(df, by_col, target_col, agg="mean"):
    if agg == "sum":
        g = df.groupby(by_col)[target_col].sum().reset_index(name="valor")
    else:
        g = df.groupby(by_col)[target_col].mean().reset_index(name="valor")
    g = g.sort_values(by_col)
    return g["valor"].tolist()

# --- 1. WELLNESS GLOBAL PROMEDIO ---
wellness_prom = round(df_periodo["wellness_score"].mean(), 1)

if periodo == "Último día":
    chart_wellness = [wellness_prom]
    delta_wellness = 0
elif periodo == "Semana":
    trend_wellness = (
        df.groupby("semana")["wellness_score"]
        .mean()
        .reset_index(name="promedio")
        .sort_values("semana")
    )
    chart_wellness = trend_wellness["promedio"].tolist()
    delta_wellness = calc_delta(chart_wellness)
else:  # Mes
    trend_wellness = (
        df.groupby("mes")["wellness_score"]
        .mean()
        .reset_index(name="promedio")
        .sort_values("mes")
    )
    chart_wellness = trend_wellness["promedio"].tolist()
    delta_wellness = calc_delta(chart_wellness)

# --- 2. RPE PROMEDIO ---
rpe_prom = round(df_periodo["rpe"].mean(), 1)

if periodo == "Último día":
    chart_rpe = [rpe_prom]
    delta_rpe = 0
elif periodo == "Semana":
    trend_rpe = (
        df.groupby("semana")["rpe"]
        .mean()
        .reset_index(name="rpe_prom")
        .sort_values("semana")
    )
    chart_rpe = trend_rpe["rpe_prom"].tolist()
    delta_rpe = calc_delta(chart_rpe)
else:  # Mes
    trend_rpe = (
        df.groupby("mes")["rpe"]
        .mean()
        .reset_index(name="rpe_prom")
        .sort_values("mes")
    )
    chart_rpe = trend_rpe["rpe_prom"].tolist()
    delta_rpe = calc_delta(chart_rpe)

# --- 3. CARGA TOTAL (UA) ---
ua_total = int(df_periodo["ua"].sum())

if periodo == "Último día":
    chart_ua = [ua_total]
    delta_ua = 0
elif periodo == "Semana":
    trend_ua = (
        df.groupby("semana")["ua"]
        .sum()
        .reset_index(name="ua_total")
        .sort_values("semana")
    )
    chart_ua = trend_ua["ua_total"].tolist()
    delta_ua = calc_delta(chart_ua)
else:  # Mes
    trend_ua = (
        df.groupby("mes")["ua"]
        .sum()
        .reset_index(name="ua_total")
        .sort_values("mes")
    )
    chart_ua = trend_ua["ua_total"].tolist()
    delta_ua = calc_delta(chart_ua)

# --- 4. ALERTAS (jugadoras con wellness <15 o dolor >3) ---

jugadoras_riesgo = (
    df_periodo.groupby("id_jugadora", as_index=False)
    .agg(en_riesgo=("id_jugadora", lambda _: ((df_periodo["wellness_score"] < 15) | (df_periodo["dolor"] > 3)).any()))
)

# 2️⃣ Contar jugadoras en riesgo (True) y total de jugadoras únicas
alertas_count = jugadoras_riesgo[jugadoras_riesgo["en_riesgo"]].shape[0]
total_jugadoras = jugadoras_riesgo.shape[0]
if total_jugadoras == 0:
    total_jugadoras = 1  # evitar división por cero

# 3️⃣ Porcentaje real de jugadoras en zona roja
alertas_pct = round((alertas_count / total_jugadoras) * 100, 1)

# 4️⃣ --- Tendencia dependiente del periodo ---
if periodo == "Último día":
    chart_alertas = [alertas_pct]
    delta_alertas = 0

elif periodo == "Semana":
    # Agrupar por semana y calcular % de jugadoras únicas en riesgo por semana
    trend_alertas = (
        df.groupby(["semana", "id_jugadora"])
        .apply(lambda x: ((x["wellness_score"] < 15) | (x["dolor"] > 3)).any())
        .reset_index(name="en_riesgo")
        .groupby("semana")["en_riesgo"]
        .mean()
        .reset_index(name="pct_alertas")
        .sort_values("semana")
    )
    trend_alertas["pct_alertas"] *= 100
    chart_alertas = trend_alertas["pct_alertas"].tolist()
    delta_alertas = calc_delta(chart_alertas)

else:  # Mes
    trend_alertas = (
        df.groupby(["mes", "id_jugadora"], group_keys=False)
        .apply(lambda x: ((x["wellness_score"] < 15) | (x["dolor"] > 3)).any())
        .reset_index(name="en_riesgo")
        .groupby("mes")["en_riesgo"]
        .mean()
        .reset_index(name="pct_alertas")
        .sort_values("mes")
    )
    trend_alertas["pct_alertas"] *= 100
    chart_alertas = trend_alertas["pct_alertas"].tolist()
    delta_alertas = calc_delta(chart_alertas)


# --- PRESENTACIÓN VISUAL ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Bienestar promedio del grupo",
        f"{wellness_prom if not pd.isna(wellness_prom) else 0}/25",
        f"{delta_wellness:+.1f}%",
        chart_data=chart_wellness,
        chart_type="area",
        border=True,
        delta_color="normal",
        help=f"Promedio de bienestar global ({articulo}). Suma de recuperación, fatiga, sueño, estrés y dolor."
    )

with col2:
    st.metric(
        "Esfuerzo percibido promedio (RPE)",
        f"{rpe_prom if not pd.isna(rpe_prom) else 0}",
        f"{delta_rpe:+.1f}%",
        chart_data=chart_rpe,
        chart_type="line",
        border=True,
        delta_color="inverse",  # 🔴 más alto = más esfuerzo
        help=f"Promedio del esfuerzo percibido por las jugadoras en {articulo}."
    )

with col3:
    st.metric(
        "Carga interna total (UA)",
        ua_total,
        f"{delta_ua:+.1f}%",
        chart_data=chart_ua,
        chart_type="area",
        border=True,
        delta_color="normal",
        help=f"Suma de todas las cargas internas (RPE × minutos) registradas en {articulo}."
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
        help=f"{alertas_count} de {total_jugadoras} jugadoras ({alertas_pct}%) presentan bienestar <15 o dolor >3 en {articulo}."
    )

show_interpretation(wellness_prom, rpe_prom, ua_total, alertas_count, alertas_pct, delta_ua, total_jugadoras)

# === BRIEFING AUTOMÁTICO ===
# Crear resumen de una línea para el cuerpo técnico
estado_bienestar = (
    "óptimo" if wellness_prom > 20 else
    "moderado" if wellness_prom >= 15 else
    "en fatiga"
)

if rpe_prom is None or rpe_prom == 0 or pd.isna(rpe_prom):
    nivel_rpe = "sin datos"
elif rpe_prom < 5:
    nivel_rpe = "bajo"
elif rpe_prom <= 7:
    nivel_rpe = "moderado"
else:
    nivel_rpe = "alto"

if alertas_count == 0:
    estado_alertas = "sin jugadoras en zona roja"
elif alertas_count == 1:
    estado_alertas = "1 jugadora en seguimiento"
else:
    estado_alertas = f"{alertas_count} jugadoras en zona roja"


#st.divider()
st.markdown(
    f":material/description: **Resumen técnico:** El grupo muestra un estado de bienestar **{estado_bienestar}** "
    f"({wellness_prom}/25) con un esfuerzo percibido **{nivel_rpe}** (RPE {rpe_prom if not pd.isna(rpe_prom) else 0}). "
    f"La carga total acumulada es de **{ua_total} UA** y actualmente hay **{estado_alertas}**."
)

st.divider()
st.markdown("**Registros del periodo seleccionado**")
st.dataframe(clean_df(df_periodo), hide_index=True)

def generar_resumen_periodo(df_periodo: pd.DataFrame):
    """Tabla resumen del periodo con promedios, colores wellness y exclusión de valores nulos."""

    if df_periodo.empty:
        st.info("No hay registros disponibles en este periodo.")
        return

    # ======================================================
    # 🧱 Base y preprocesamiento
    # ======================================================
    df_periodo["Jugadora"] = (
        df_periodo["nombre"].fillna("") + " " + df_periodo["apellido"].fillna("")
    ).str.strip()

    df_in = df_periodo[df_periodo["tipo"].str.lower() == "checkin"].copy()
    df_out = df_periodo[df_periodo["tipo"].str.lower() == "checkout"].copy()

    cols_wellness = ["recuperacion", "energia", "sueno", "stress", "dolor"]

    # --- Promedios generales ---
    ## Resumen Checkin
    resumen_in = (
        df_in.groupby("Jugadora", as_index=False)[cols_wellness].mean()
    )

    # 1) Pasar a numérico (coerce) y limpiar "None"/"null"
    for c in cols_wellness:
        if c in resumen_in.columns:
            resumen_in[c] = (
                resumen_in[c]
                .replace({"None": np.nan, "none": np.nan, "null": np.nan})
                .apply(pd.to_numeric, errors="coerce")
            )

    # 2) Promedio 1–5 (NaN se ignora; si todas son NaN → NaN)
    resumen_in["Promedio_Wellness"] = resumen_in[cols_wellness].mean(axis=1, skipna=True)

    # Si quieres tratar "todo NaN" como 0 (tu petición):
    resumen_in["Promedio_Wellness"] = resumen_in["Promedio_Wellness"].fillna(0)

    # 3) Dolor a numérico y NaN->0 (para comparar)
    if "dolor" in resumen_in.columns:
        resumen_in["dolor"] = pd.to_numeric(resumen_in["dolor"], errors="coerce").fillna(0)
    else:
        resumen_in["dolor"] = 0
    
    # 4) Riesgo: elige **UNA** de estas dos lógicas:

    # A) Usando escala 25 puntos (mantiene tu umbral 15):
    resumen_in["En_riesgo"] = (resumen_in["Promedio_Wellness"]*5 < 15) | (resumen_in["dolor"] > 3)

    #st.dataframe(resumen_in)
    #resumen_in["Promedio_Wellness"] = resumen_in[cols_wellness].mean(axis=1)
    #resumen_in["En_riesgo"] = (resumen_in["Promedio_Wellness"] < 15) | (resumen_in["dolor"] > 3)

    ## Resumen Checkout
    resumen_out = (
        df_out.groupby("Jugadora", as_index=False)
        .agg(RPE_promedio=("rpe", "mean"), UA_total=("ua", "mean"))
    )

    resumen = pd.merge(resumen_in, resumen_out, on="Jugadora", how="outer")
    
    resumen = resumen.fillna(0)
    resumen.index = resumen.index + 1
    # Asegurar consistencia de tipos y llenar vacíos
    #resumen["Promedio_Wellness"] = resumen["Promedio_Wellness"].fillna(0)
    resumen["En_riesgo"] = resumen["En_riesgo"].fillna(False)

    # Si deseas mantener el formato “Sí/No/” en texto:
    resumen["En_riesgo"] = (resumen["Promedio_Wellness"]*5 < 15) | (resumen_in["dolor"] > 3)

    # --- Renombrar y reorganizar columnas ---
    resumen = resumen.rename(columns={
        "recuperacion": "Recuperación",
        "energia": "Energía",
        "sueno": "Sueño",
        "stress": "Estrés",
        "dolor": "Dolor"
    })[[
        "Jugadora", "Recuperación", "Energía", "Sueño", "Estrés", "Dolor",
        "Promedio_Wellness", "RPE_promedio", "UA_total", "En_riesgo"
    ]]

    # --- Eliminar filas sin datos útiles ---
    resumen = resumen.dropna(
        subset=["Recuperación", "Energía", "Sueño", "Estrés", "Dolor", "RPE_promedio", "UA_total"],
        how="all"
    ).copy()

    # --- Convertir En_riesgo a texto (Sí / No / vacío) ---
    resumen["En_riesgo"] = resumen["En_riesgo"].apply(lambda x: "Sí" if x is True else ("No" if x is False else ""))
    # ======================================================
    # 🎨 Colores
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
    # 📈 Aplicar estilo visual
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

    st.dataframe(styled)
