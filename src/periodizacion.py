import streamlit as st
import pandas as pd
from src.styles import WELLNESS_COLOR_NORMAL, WELLNESS_COLOR_INVERTIDO

def mostrar_tabla_referencia_wellness():
    """Tabla de referencia explicativa (1-5) con colores tipo semáforo y escalas invertidas en Estrés y Dolor."""

    # --- Datos base ---
    data = {
        "Variable": ["Recuperación", "Energía", "Sueño", "Estrés", "Dolor"],
        "1": [
            "Muy mal recuperado",
            "Extremadamente cansado",
            "Muy mala calidad / Insomnio",
            "Muy relajado / Positivo",
            "Sin dolor"
        ],
        "2": [
            "Más fatigado de lo normal",
            "Fatigado",
            "Sueño inquieto o corto",
            "Relajado",
            "Dolor leve"
        ],
        "3": [
            "Normal",
            "Normal",
            "Sueño aceptable",
            "Estrés controlado",
            "Molestias leves"
        ],
        "4": [
            "Recuperado",
            "Ligera fatiga / Buen estado",
            "Buena calidad de sueño",
            "Alto nivel de estrés",
            "Dolor moderado"
        ],
        "5": [
            "Totalmente recuperado",
            "Energía Máxima",
            "Excelente descanso",
            "Muy estresado / Irritable",
            "Dolor severo"
        ],
    }

    df_ref = pd.DataFrame(data).set_index("Variable")

    # --- Función de color por celda (usando estilos globales) ---
    def color_by_col(col):
        if col.name not in ["1", "2", "3", "4", "5"]:
            return [""] * len(col)

        result = []
        for var in df_ref.index:
            # Seleccionar paleta normal o invertida según variable
            cmap = WELLNESS_COLOR_INVERTIDO if var in ["Estrés", "Dolor"] else WELLNESS_COLOR_NORMAL
            color = cmap[int(col.name)]
            result.append(
                f"background-color:{color}; color:white; text-align:center; font-weight:bold;"
            )
        return result

    # --- Aplicar estilo ---
    styled_df = df_ref.style.apply(color_by_col, subset=["1", "2", "3", "4", "5"], axis=0)

    # --- Mostrar tabla en Streamlit ---
    with st.expander("Ver tabla de referencia de escalas (1–5)"):
        st.dataframe(styled_df, hide_index=False)
        st.caption(
            "**Interpretación:**\n"
            "- En **Recuperación**, **Energía** y **Sueño** → valores altos indican bienestar.\n"
            "- En **Estrés** y **Dolor** → valores bajos indican bienestar (escala invertida)."
        )

def grafico():
    import pandas as pd
    import plotly.express as px

    data = {
        "Dia": ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD0", "MD+1"],
        "Carga": [2, 4, 6, 8, 6, 5, 9, 3],
    }

    df = pd.DataFrame(data)
    fig = px.area(df, x="Dia", y="Carga", title="Onda de carga del microciclo (periodización táctica)")
    fig.update_traces(line_color="red", fillcolor="rgba(255,0,0,0.3)")
    fig.update_yaxes(title_text="Intensidad / Carga interna")
    st.plotly_chart(fig)

