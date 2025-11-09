import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import altair as alt

from src.styles import get_color_wellness, BRAND_PRIMARY, BRAND_TEXT

# 1️⃣ RPE y UA -------------------------------------------------------
def grafico_rpe_ua(df: pd.DataFrame):
    #st.markdown("#### Evolución de RPE y Carga Interna (UA)")
    if "ua" in df.columns and "rpe" in df.columns:
        fig = px.bar(
            df,
            x="fecha_sesion",
            y="ua",
            color="rpe",
            color_continuous_scale="RdYlGn_r",
            labels={"ua": "Carga Interna (UA)", "fecha_sesion": "Fecha", "rpe": "RPE"},
            title="Evolución de RPE (color) y Carga Interna (barras)"
        )
        st.plotly_chart(fig)
    else:
        st.info("No hay datos de RPE o UA para graficar.")


# 2️⃣ Duración vs RPE ------------------------------------------------
def grafico_duracion_rpe(df: pd.DataFrame):
    #st.markdown("#### Relación entre duración y esfuerzo percibido")
    if "minutos_sesion" in df.columns and "rpe" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["fecha_sesion"],
            y=df["minutos_sesion"],
            name="Minutos",
            marker_color="#1976D2"
        ))
        fig.add_trace(go.Scatter(
            x=df["fecha_sesion"],
            y=df["rpe"],
            mode="lines+markers",
            name="RPE",
            yaxis="y2",
            line=dict(color="#E64A19", width=3)
        ))
        fig.update_layout(
            title="Relación entre duración y esfuerzo percibido",
            yaxis=dict(title="Minutos de sesión"),
            yaxis2=dict(title="RPE", overlaying="y", side="right"),
            legend_title_text="Variables"
        )
        st.plotly_chart(fig)
    else:
        st.info("No hay datos de minutos o RPE para graficar.")


# 3️⃣ ACWR -----------------------------------------------------------
def grafico_acwr(df: pd.DataFrame):
    #st.markdown("#### Evolución del índice ACWR (Relación Agudo:Crónico)")

    if "ua" not in df.columns:
        st.info("No hay datos de carga interna (UA) para calcular ACWR.")
        return

    df = df.copy()
    df["ua"] = pd.to_numeric(df["ua"], errors="coerce")
    df["acute7"] = df["ua"].rolling(7, min_periods=3).mean()
    df["chronic28"] = df["ua"].rolling(28, min_periods=7).mean()
    df["acwr"] = df["acute7"] / df["chronic28"]
    df = df.dropna(subset=["acwr"])

    if df.empty:
        st.info("No hay suficientes datos para calcular ACWR.")
        return

    def _zone(v: float) -> str:
        if v < 0.8: return "Subcarga"
        elif v < 1.3: return "Sweet Spot"
        elif v < 1.5: return "Elevada"
        else: return "Peligro"

    df["zona"] = df["acwr"].apply(_zone)

    bandas = pd.DataFrame([
        {"y0": 0.0, "y1": 0.8, "color": "#E3F2FD"},
        {"y0": 0.8, "y1": 1.3, "color": "#C8E6C9"},
        {"y0": 1.3, "y1": 1.5, "color": "#FFE0B2"},
        {"y0": 1.5, "y1": 3.0, "color": "#FFCDD2"}
    ])

    bg = alt.Chart(bandas).mark_rect(opacity=0.6).encode(
        y="y0:Q", y2="y1:Q",
        color=alt.Color("color:N", scale=None, legend=None)
    )

    rules = alt.Chart(pd.DataFrame({"y": [0.8, 1.3, 1.5]})).mark_rule(
        color="black", strokeDash=[4, 2], opacity=0.7
    ).encode(y="y:Q")

    base = alt.Chart(df).encode(
        x=alt.X("fecha_sesion:T", title="Fecha", axis=alt.Axis(format="%b %d")),
        y=alt.Y("acwr:Q", title="ACWR", scale=alt.Scale(domain=[0, max(2.5, df["acwr"].max() + 0.2)]))
    )

    line = base.mark_line(color="black", strokeWidth=2, interpolate="monotone")
    pts = base.mark_circle(size=70).encode(
        color=alt.Color("zona:N", scale=alt.Scale(
            domain=["Subcarga", "Sweet Spot", "Elevada", "Peligro"],
            range=["#64B5F6", "#2ca25f", "#fdae6b", "#d62728"]
        )),
        tooltip=["fecha_sesion:T", alt.Tooltip("acwr:Q", format=".2f")]
    )

    labels = alt.Chart(pd.DataFrame([
        {"y": 0.4, "text": "Subcarga"},
        {"y": 1.05, "text": "Punto Óptimo"},
        {"y": 1.4, "text": "Zona Elevada"},
        {"y": 1.8, "text": "Peligro"}
    ])).mark_text(align="left", dx=5, fontSize=11, color="#444").encode(y="y:Q", text="text:N")

    chart = alt.layer(bg, rules, line, pts, labels).properties(height=320, width="container", title="Evolución del índice ACWR (Relación Agudo:Crónico)")
    st.altair_chart(chart)


# 4️⃣ Wellness -------------------------------------------------------
def grafico_wellness(df: pd.DataFrame):
    #st.markdown("**Evolución de los indicadores de bienestar (1-5)**")
    cols = ["recuperacion", "energia", "sueno", "stress", "dolor"]
    if all(c in df.columns for c in cols):
        fig = px.line(
            df, x="fecha_sesion", y=cols, markers=True,
            labels={"value": "Nivel (1-5)", "fecha_sesion": "Fecha", "variable": "Parámetro"},
            title="Evolución de los indicadores de bienestar"
        )
        st.plotly_chart(fig)
    else:
        st.info("No hay datos de bienestar para graficar.")


# 5️⃣ Riesgo de lesión -----------------------------------------------
def grafico_riesgo_lesion(df: pd.DataFrame):
    """
    Visualiza el riesgo de lesión combinando el índice ACWR (Agudo:Crónico)
    con la fatiga subjetiva, mostrando zonas de carga de fondo.
    """

    st.markdown("#### 🧠 Evolución del riesgo de lesión (ACWR + Fatiga)")

    if "ua" not in df.columns:
        st.info("No hay datos suficientes para calcular el riesgo.")
        return

    df = df.copy()
    df["ua"] = pd.to_numeric(df["ua"], errors="coerce")
    df["fatiga"] = pd.to_numeric(df.get("energia", np.nan), errors="coerce")

    # Calcular cargas aguda y crónica
    df["acute7"] = df["ua"].rolling(7, min_periods=3).mean()
    df["chronic28"] = df["ua"].rolling(28, min_periods=7).mean()
    df["acwr"] = df["acute7"] / df["chronic28"]

    # --- Clasificación del riesgo ---
    def riesgo_calc(row):
        if pd.isna(row["acwr"]) or pd.isna(row["fatiga"]):
            return np.nan
        if row["acwr"] > 1.5 or row["fatiga"] >= 4:
            return "Alto"
        elif 1.3 <= row["acwr"] <= 1.5 or 3 <= row["fatiga"] < 4:
            return "Moderado"
        else:
            return "Bajo"

    df["riesgo_lesion"] = df.apply(riesgo_calc, axis=1)

    # --- Mapa de colores ---
    color_map = {"Bajo": "#43A047", "Moderado": "#FB8C00", "Alto": "#E53935"}

    # --- Gráfico base ---
    fig = px.scatter(
        df,
        x="fecha_sesion",
        y="acwr",
        color="riesgo_lesion",
        color_discrete_map=color_map,
        title="Evolución del riesgo de lesión (ACWR + Fatiga)",
        labels={
            "acwr": "Relación Agudo:Crónico (ACWR)",
            "fecha_sesion": "Fecha",
            "riesgo_lesion": "Nivel de riesgo"
        },
        hover_data={
            "acwr": ":.2f",
            "fatiga": ":.1f",
            "riesgo_lesion": True
        }
    )

    # --- Bandas de color de fondo según ACWR ---
    fig.add_hrect(y0=0.0, y1=0.8, fillcolor="#BBDEFB", opacity=0.25, line_width=0)   # Azul: subcarga
    fig.add_hrect(y0=0.8, y1=1.3, fillcolor="#C8E6C9", opacity=0.25, line_width=0)   # Verde: zona óptima
    fig.add_hrect(y0=1.3, y1=1.5, fillcolor="#FFE0B2", opacity=0.25, line_width=0)   # Naranja: elevada
    fig.add_hrect(y0=1.5, y1=3.0, fillcolor="#FFCDD2", opacity=0.25, line_width=0)   # Roja: riesgo

    # --- Estética ---
    fig.update_layout(
        yaxis=dict(range=[0.7, max(2.0, df["acwr"].max() + 0.2)]),
        legend_title_text="Nivel de riesgo",
        template="simple_white"
    )

    st.plotly_chart(fig)

    # --- Leyenda explicativa ---
    st.markdown(
        """
        **Interpretación del gráfico:**
        - 🟩 **Banda verde (0.8–1.3):** zona óptima o “sweet spot”.  
        - 🟧 **Banda naranja (1.3–1.5):** carga elevada, riesgo moderado.  
        - 🟥 **Banda roja (>1.5):** sobrecarga, riesgo alto de lesión.  
        - 🟦 **Banda azul (<0.8):** subcarga o pérdida de forma.  
        - El **color del punto** depende del riesgo combinado entre **ACWR y fatiga**:
            - 🟢 **Bajo:** carga estable y fatiga baja.  
            - 🟠 **Moderado:** aumento de carga o fatiga leve.  
            - 🔴 **Alto:** sobrecarga o fatiga elevada.
        """
    )

def tabla_wellness_individual(df: pd.DataFrame):
    """
    Muestra una tabla detallada por fecha con indicadores de bienestar (1-5)
    aplicando la escala de interpretación Wellness global (normal e invertida).
    """

    st.markdown("**Wellness por sesión**")

    # --- Verificar columnas necesarias ---
    cols_min = ["fecha_sesion", "periodizacion_tactica", "energia", "recuperacion", "sueno", "stress", "dolor"]
    if not all(c in df.columns for c in cols_min):
        st.warning("No hay suficientes datos para mostrar la tabla de Wellness.")
        return

    # --- Crear tabla base ---
    t = df.copy()
    t["fecha_sesion"] = pd.to_datetime(t["fecha_sesion"], errors="coerce")
    t = t.sort_values("fecha_sesion", ascending=False).reset_index(drop=True)

    # Día de la semana en español
    t["Día Semana"] = t["fecha_sesion"].dt.day_name(locale="es_ES")
    t["fecha_sesion"] = t["fecha_sesion"].dt.date

    # Tipo de estímulo y readaptación
    t["Tipo de estímulo"] = t.get("tipo_estimulo", "").fillna("").astype(str)
    t["Tipo de readaptación"] = t.get("tipo_readaptacion", "").fillna("").astype(str)

    # Calcular Promedio Wellness
    t["Promedio Wellness"] = t[["recuperacion", "energia", "sueno", "stress", "dolor"]].mean(axis=1)

    # Selección y renombre de columnas
    t_show = t[[
        "fecha_sesion", "Día Semana", "periodizacion_tactica",
        "Tipo de estímulo", "Tipo de readaptación",
        "recuperacion", "energia", "sueno", "stress", "dolor", "Promedio Wellness"
    ]].rename(columns={
        "fecha_sesion": "Fecha sesión",
        "periodizacion_tactica": "Periodización táctica",
        "recuperacion": "Recuperación",
        "energia": "Energía",
        "sueno": "Sueño",
        "stress": "Estrés",
        "dolor": "Dolor"
    })

    # --- Aplicar colores desde styles.py ---
    def style_func(col):
        if col.name in ["Recuperación", "Energía", "Sueño", "Estrés", "Dolor"]:
            return [
                f"background-color:{get_color_wellness(v, col.name)}; "
                f"color:white; font-weight:bold; text-align:center;"
                for v in col
            ]
        elif col.name == "Promedio Wellness":
            return [
                # Verde óptimo, amarillo moderado, rojo bajo
                "background-color:#27AE60; color:white; font-weight:bold; text-align:center;" if v >= 4 else
                "background-color:#F1C40F; color:black; text-align:center;" if 3 <= v < 4 else
                "background-color:#E74C3C; color:white; font-weight:bold; text-align:center;"
                for v in col
            ]
        return [""] * len(col)

    # --- Aplicar estilo al DataFrame ---
    styled = (
        t_show.style
        .apply(style_func, subset=["Recuperación", "Energía", "Sueño", "Estrés", "Dolor", "Promedio Wellness"])
        .format(precision=2)
    )

    st.dataframe(styled)

    # --- Explicación ---
    st.caption(
        "🟩 **Valores altos indican mejor bienestar** en Recuperación, Energía y Sueño.  \n"
        "🟥 **Valores bajos indican mejor bienestar** en Estrés y Dolor (escala invertida)."
    )
