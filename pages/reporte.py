import pandas as pd
import streamlit as st
import plotly.express as px
import datetime
import src.config as config
config.init_config()

from src.auth import init_app_state, login_view, menu
init_app_state()

from src.ui_components import selection_header
from src.db_records import get_records_wellness_db, load_jugadoras_db, load_competiciones_db

# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()

st.header('Reporte :red[Individual]', divider=True)

menu()

jug_df, jug_error = load_jugadoras_db()
comp_df, comp_error = load_competiciones_db()

jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, modo="reporte")

if not jugadora:
    st.info("Selecciona una jugadora para continuar.")
    st.stop()

records = get_records_wellness_db()
records = records[records["identificacion"]==jugadora["identificacion"]]
#df_filtrado = records[records["periodizacion_tactica"] <= 1]
st.dataframe(records)

def mostrar_onda_microciclo(registros):

    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha_hora"]).dt.date

    # Mantener últimos 15 días
    df = df.sort_values("fecha").tail(15)

    # Calcular UA promedio por día y normalizar por periodización táctica
    df_group = (
        df.groupby("periodizacion_tactica", as_index=False)
          .agg({"ua": "mean"})
          .sort_values("periodizacion_tactica")
    )

    # --- Gráfico tipo onda ---
    fig = px.area(
        df_group,
        x="periodizacion_tactica",
        y="ua",
        markers=True,
        title="📈 Onda de carga interna (UA promedio por día relativo al partido)",
    )
    fig.update_traces(line_color="#e74c3c", fillcolor="rgba(231,76,60,0.3)")
    fig.update_layout(
        xaxis_title="Periodo táctico (MD–6 → MD+1)",
        yaxis_title="Carga interna (UA)",
        template="plotly_white"
    )
    st.plotly_chart(fig)

def mostrar_periodizacion_semana(registros):
    """
    Muestra la evolución de la periodización táctica (MD–6 a MD+1)
    en los últimos 7 días, usando fechas en el eje X y valores de
    periodización táctica en el eje Y.
    """

    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha_hora"]).dt.date

    # Tomar últimos 7 días
    hoy = datetime.date.today()
    ultimos_7 = [hoy - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    df = df[df["fecha"].isin(ultimos_7)]

    # Convertir a nombre de día en español
    dias_es = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }
    df["dia_semana"] = pd.to_datetime(df["fecha"]).dt.day_name().map(dias_es)

    # Promedio diario de la periodización
    df_group = (
        df.groupby(["fecha", "dia_semana"], as_index=False)
          .agg({"periodizacion_tactica": "mean"})
          .sort_values("fecha")
    )

    # --- Gráfico de evolución de periodización ---
    fig = px.line(
        df_group,
        x="dia_semana",
        y="periodizacion_tactica",
        markers=True,
        title=":material/timeline: Periodización táctica semanal (últimos 7 días)",
    )
    fig.update_traces(line_color="#0074D9")
    fig.update_layout(
        xaxis_title="Día de la semana",
        yaxis_title="Periodización táctica (MD–6 → MD+1)",
        yaxis=dict(dtick=1, range=[-6.5, 1.5]),
        template="plotly_white",
    )

    st.plotly_chart(fig)

    # Mostrar tabla resumen
    st.dataframe(df_group[["dia_semana", "periodizacion_tactica"]], hide_index=True)

    return df_group

import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from scipy.interpolate import make_interp_spline

def mostrar_periodizacion_ultimos_registros(registros, cantidad):
    """
    Muestra los últimos 7 registros de periodización táctica (MD–6 a MD+1)
    con una curva suavizada tipo onda.
    """

    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha_hora"]).dt.date

    # Tomar los 7 registros más recientes
    df = df.sort_values("fecha").tail(cantidad).reset_index(drop=True)

    # Etiqueta de fecha para eje X
    dias_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    df["dia_semana"] = pd.to_datetime(df["fecha"]).dt.day_name().map(dias_es)
    df["label_fecha"] = df["dia_semana"].str[:3] + " " + df["fecha"].astype(str)

    # --- Interpolación cúbica (suavizado de curva) ---
    x = np.arange(len(df))
    y = df["periodizacion_tactica"].values

    # Crear spline suave (solo si hay al menos 4 puntos)
    if len(df) >= 4:
        x_new = np.linspace(x.min(), x.max(), 200)  # más puntos intermedios
        spline = make_interp_spline(x, y, k=3)
        y_smooth = spline(x_new)

        # Crear DataFrame interpolado para graficar
        df_smooth = pd.DataFrame({
            "x_smooth": x_new,
            "y_smooth": y_smooth
        })
    else:
        df_smooth = pd.DataFrame({"x_smooth": x, "y_smooth": y})

    # --- Gráfico ---
    fig = px.line(
        df_smooth,
        x="x_smooth",
        y="y_smooth",
        title=":material/timeline: Últimos 7 registros de periodización táctica (curva suavizada)"
    )
    fig.update_traces(line_color="#0034C8", line_width=3)
    fig.update_layout(
        xaxis_title="Registros recientes",
        yaxis_title="Periodización táctica (MD–6 → MD+1)",
        yaxis=dict(dtick=1, range=[-6.5, 1.5]),
        xaxis=dict(showticklabels=False),  # oculta ticks numéricos
        template="plotly_white"
    )

    # Añadir los puntos reales como marcadores
    fig.add_scatter(
        x=x,
        y=y,
        mode="markers+text",
        marker=dict(size=8, color="#AA0032"),
        text=df["label_fecha"],
        textposition="top center",
        showlegend=False
    )

#mostrar_onda_microciclo(df_filtrado)
#mostrar_periodizacion_semana(records)

#mostrar_periodizacion_ultimos_registros(df_filtrado, 15)