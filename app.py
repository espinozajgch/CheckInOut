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
df["wellness_score"] = df[["recuperacion", "fatiga", "sueno", "stress", "dolor"]].sum(axis=1)

# Selector de periodo
periodo = st.radio(
    "Tendencias:",
    ["Último día", "Semana", "Mes"],
    horizontal=True,
    index=0  # "Último día" por defecto
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
    df_periodo.groupby("identificacion", as_index=False)
    .agg(en_riesgo=("identificacion", lambda _: ((df_periodo["wellness_score"] < 15) | (df_periodo["dolor"] > 3)).any()))
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
        df.groupby(["semana", "identificacion"])
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
        df.groupby(["mes", "identificacion"], group_keys=False)
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


#st.divider()
show_interpretation(wellness_prom, rpe_prom, ua_total, alertas_count, alertas_pct, delta_ua, total_jugadoras)

# === BRIEFING AUTOMÁTICO ===
# Crear resumen de una línea para el cuerpo técnico
estado_bienestar = (
    "óptimo" if wellness_prom > 20 else
    "moderado" if wellness_prom >= 15 else
    "en fatiga"
)

nivel_rpe = (
    "bajo" if rpe_prom < 5 else
    "moderado" if rpe_prom <= 7 else
    "alto"
)

if alertas_count == 0:
    estado_alertas = "sin jugadoras en zona roja"
elif alertas_count == 1:
    estado_alertas = "1 jugadora en seguimiento"
else:
    estado_alertas = f"{alertas_count} jugadoras en zona roja"

st.caption(
    "🟢 / 🔴 Los colores en los gráficos muestran *variaciones* respecto al periodo anterior "
    "(🔺 sube, 🔻 baja). Los colores en la interpretación reflejan *niveles fisiológicos* "
    "según umbrales deportivos."
)

st.divider()
st.markdown(
    f"📋 **Resumen técnico:** El grupo muestra un estado de bienestar **{estado_bienestar}** "
    f"({wellness_prom}/25) con un esfuerzo percibido **{nivel_rpe}** (RPE {rpe_prom}). "
    f"La carga total acumulada es de **{ua_total} UA** y actualmente hay **{estado_alertas}**."
)

st.divider()
st.markdown("**Registros del periodo seleccionado**")
st.dataframe(clean_df(df_periodo), hide_index=True)