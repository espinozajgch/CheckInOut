import streamlit as st
import pandas as pd
import datetime
from .schema import DIAS_SEMANA, PERIODIZACION

# ======================================================
# 1️⃣ PROPUESTA CLÁSICA: Periodización táctica (– / + / 0)
# ======================================================
def periodizacion_por_dia(record: dict, dia_partido: str = "Domingo"):
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    partido_idx = dias_semana.index(dia_partido)

    dia = st.selectbox("📅 Día de entrenamiento", dias_semana, index=0, key="select_dia_por_dia")
    idx = dias_semana.index(dia)
    relacion = idx - partido_idx

    if relacion < 0:
        etiqueta = f"MD{relacion}"
        color = "orange" if relacion > -3 else "red"
        texto = "Día de preparación antes del partido"
    elif relacion == 0:
        etiqueta, color, texto = "MD", "red", "Día de partido"
    else:
        etiqueta, color, texto = f"MD+{relacion}", "blue", "Día posterior al partido"

    st.markdown(f"<p style='color:{color}; font-weight:bold;'>🧭 {etiqueta} — {texto}</p>", unsafe_allow_html=True)

    record["periodizacion_tipo"] = "por_dia"
    record["dia_semana"] = dia
    record["relacion_partido"] = relacion
    record["etiqueta_md"] = etiqueta
    return record


def periodizacion_doble(record: dict, dia_partido: str = "Domingo"):
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    tipos_carga = ["Regenerativo", "Carga alta", "Carga media", "Activación", "Partido", "Descanso"]

    c1, c2 = st.columns(2)
    with c1:
        dia = st.selectbox("📅 Día de entrenamiento", dias_semana, index=0, key="select_dia_doble")
    with c2:
        tipo = st.selectbox("⚙️ Tipo de carga táctica", tipos_carga, index=1, key="select_tipo_doble")

    partido_idx = dias_semana.index(dia_partido)
    idx = dias_semana.index(dia)
    relacion = idx - partido_idx

    colores = {
        "Regenerativo": ("blue", "Recuperación o trabajo regenerativo"),
        "Carga alta": ("orange", "Alta carga táctica/física"),
        "Carga media": ("orange", "Carga moderada o técnica"),
        "Activación": ("green", "Activación pre-partido"),
        "Partido": ("red", "Día de competición (MD)"),
        "Descanso": ("gray", "Descanso o día libre"),
    }

    color, texto = colores.get(tipo, ("white", ""))
    st.markdown(f"<p style='color:{color}; font-weight:bold;'>⚽ {texto}</p>", unsafe_allow_html=True)

    record["periodizacion_tipo"] = "doble"
    record["dia_semana"] = dia
    record["tipo_carga_tactica"] = tipo
    record["relacion_partido"] = relacion
    return record


def tactical_periodization_block(record: dict, microciclo_dias: int = 6, partidos_semana: int = 1):
    if partidos_semana >= 2:
        min_val, max_val = -3, 1
    else:
        if microciclo_dias <= 4:
            min_val, max_val = -3, 0
        elif microciclo_dias == 5:
            min_val, max_val = -4, 0
        else:
            min_val, max_val = -6, 1

    descripciones = {
        -6: ("⚪ Carga regenerativa o base", "gray"),
        -5: ("⚪ Carga general o acumulación", "gray"),
        -4: ("🟡 Carga moderada (fuerza/técnica)", "orange"),
        -3: ("🟠 Carga alta (físico-táctica)", "orange"),
        -2: ("🟠 Carga media con componente táctico", "orange"),
        -1: ("🟢 Activación pre-partido", "green"),
         0: ("🔴 Día de partido", "red"),
         1: ("💧 Recuperación post-partido", "blue"),
    }

    valor = st.slider(
        "Periodización táctica (relativa al día de partido)",
        min_value=min_val, max_value=max_val, value=0, step=1, format="%d",
        key="slider_clasico",
        help="Valores negativos: días antes del partido. 0 = día del partido. Positivos: días después."
    )
    descripcion, color = descripciones.get(valor, ("", "white"))
    st.markdown(f"<p style='color:{color}; font-weight:bold;'>{descripcion}</p>", unsafe_allow_html=True)

    record["periodizacion_tipo"] = "clasica"
    record["periodizacion_valor"] = valor
    record["periodizacion_desc"] = descripcion
    return record

def periodizacion_selector(record: dict, key_prefix: str = "") -> int:
    """
    Muestra los controles sincronizados para seleccionar la periodización táctica:
    - Slider (-6 a 0)
    - Selectbox (MD+1 / MD-6 ... MD0)
    
    Args:
        record (dict): Diccionario del registro actual.
        key_prefix (str): Prefijo opcional para las claves de Streamlit (evita conflictos si se usa varias veces).
    
    Returns:
        int: Valor final de periodización táctica (-6 a 0).
    """

    # --- Función auxiliar para normalizar ---
    def _normalize_pt(v: int) -> int:
        try:
            v = int(v)
        except Exception:
            v = 0
        if v > 0:
            # Mapea +1 → -6, +6 → -1
            return max(-6, min(0, v - 7))
        return max(-6, min(0, v))

    # --- Valores iniciales ---
    raw_pt = int(record.get("periodizacion_tactica", 0) or 0)
    current_pt = _normalize_pt(raw_pt)

    # --- Layout ---
    colA, colB = st.columns([2, 1])

    with colA:
        slider_val = st.slider(
            "📊 Periodización táctica (-6 a 0)",
            min_value=-6,
            max_value=0,
            value=current_pt,
            step=1,
            key=f"{key_prefix}pt_slider",
        )

    with colB:
        md_pairs = [
            ("MD+1 / MD-6", -6),
            ("MD+2 / MD-5", -5),
            ("MD+3 / MD-4", -4),
            ("MD+4 / MD-3", -3),
            ("MD+5 / MD-2", -2),
            ("MD+6 / MD-1", -1),
            ("MD0", 0),
        ]

        # Calcular índice para el selectbox
        idx_from_slider = slider_val + 6  # mapea -6..0 → 0..6
        md_sel_label = st.selectbox(
            "📅 Matchday",
            options=[p[0] for p in md_pairs],
            index=idx_from_slider,
            key=f"{key_prefix}pt_md_select",
        )

        # Sincronizar cambios entre selectbox y slider
        selected_idx = [p[0] for p in md_pairs].index(md_sel_label)
        final_pt = md_pairs[selected_idx][1]

        #if final_pt != slider_val:
        #    st.session_state[f"{key_prefix}pt_slider"] = final_pt

    # --- Actualizar el registro y devolver ---
    record["periodizacion_tactica"] = final_pt
    return record

def periodizacion_teorica(record: dict, df_ref: dict):

    df_ref = pd.DataFrame(PERIODIZACION)

    tipos_carga = ["Regenerativo", "Carga alta", "Carga media", "Activación", "Partido", "Descanso"]

    # c1, c2 = st.columns(2)
    # with c1:
    #     dia = st.selectbox("📅 Día de entrenamiento", dias_semana, index=0, key="select_dia_doble")
    # with c2:
    #     tipo = st.selectbox("⚙️ Tipo de carga táctica", tipos_carga, index=1, key="select_tipo_doble")

    colA, colB, colC, colD  = st.columns([2,2,3,3])
    with colA:
        fecha_sesion = st.date_input("Fecha de la sesión", datetime.date.today(), disabled=True)
    with colB:
        dia_semana = fecha_sesion.strftime("%A")
        dia_semana_es = DIAS_SEMANA.get(dia_semana, dia_semana)
        #st.text_input("Día de la semana", dia_semana_es, disabled=True)
        tipo = st.selectbox("⚙️ Tipo de carga táctica", tipos_carga, index=1, key="select_tipo_doble_")

    with colC:
        dia_sel = st.selectbox(
            "+",
            options=df_ref["dia"],
            index=3,  # por defecto MD-3
        )
        
    with colD:
        dia_sel = st.selectbox(
            "-",
            options=df_ref["dia"],
            index=3,  # por defecto MD-3
        )
    fila = df_ref[df_ref["dia"] == dia_sel].iloc[0]
    st.caption(fila["descripcion_output"])

    # === 4️⃣ Mostrar información del día seleccionado ===

    # st.metric(
    #     label=f"Carga teórica para {fila['Día']}",
    #     value=f"{fila['Carga (1-10)']}/10",
    #     delta=f"{fila['Porcentaje estimado (%)']}%",
    # )
    
    # === 5️⃣ Retornar valor de carga si se necesita en otras partes ===
    #return fila["Carga (1-10)"], fila["Porcentaje estimado (%)"], fila["descripcion"]
    final_pt = fila["valor"]
    record["periodizacion_tactica"] = final_pt
    return record

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

    # --- Colores para escalas normales y reversas ---
    color_normal = {
        "1": "#e74c3c",  # rojo
        "2": "#e67e22",  # naranja
        "3": "#f1c40f",  # amarillo
        "4": "#2ecc71",  # verde claro
        "5": "#27ae60",  # verde oscuro
    }

    color_invertido = {
        "1": "#27ae60",  # verde oscuro
        "2": "#2ecc71",  # verde claro
        "3": "#f1c40f",  # amarillo
        "4": "#e67e22",  # naranja
        "5": "#e74c3c",  # rojo
    }

    # --- Función para aplicar color por columna, según variable ---
    def apply_colors(col):
        # Detectar si la columna pertenece a Estrés o Dolor
        is_invertida = col.name in ["Estrés", "Dolor"]
        cmap = color_invertido if is_invertida else color_normal

        return [
            f"background-color: {cmap.get(str(col.name), '')}; color: white; text-align: center; font-weight: bold;"
        ] * len(col)

    # --- Aplicar color por columna numérica ---
    def apply_column_color(col):
        # Detectar si variable es inversa (Estrés o Dolor)
        is_invertida = col.name in ["Estrés", "Dolor"]
        cmap = color_invertido if is_invertida else color_normal
        return [f"background-color: {cmap.get(col.name, '#ffffff')}; color: white; font-weight: bold; text-align: center;"] * len(col)

    # Crear copia y aplicar colores por columna
    def color_by_col(col):
        cmap = color_normal
        if col.name in ["1", "2", "3", "4", "5"]:
            # Para cada fila, si la variable es Estrés o Dolor → invertir
            return [
                f"background-color: {color_invertido[str(col.name)] if var in ['Estrés', 'Dolor'] else color_normal[str(col.name)]};"
                " color: white; text-align: center; font-weight: bold;"
                for var in df_ref.index
            ]
        return [""] * len(col)

    styled_df = df_ref.style.apply(color_by_col, subset=["1", "2", "3", "4", "5"], axis=0)

    # --- Mostrar tabla ---
    with st.expander("Ver tabla de referencia de escalas (1-5)"):
        st.dataframe(styled_df, hide_index=False)
        st.caption(
            "**Interpretación:**\n"
            "- En **Recuperación**, **Energía** y **Sueño** → valores altos indican bienestar.\n"
            "- En **Estrés** y **Dolor** → valores bajos indican bienestar (escala invertida)."
        )

def mostrar_tabla_periodizacion():
    """Muestra la tabla teórica de carga (MD-6 a MD+1) y permite seleccionar un día para ver su detalle."""
    # === 1️⃣ Datos base de referencia ===
    df_ref = pd.DataFrame(PERIODIZACION)

    # === 2️⃣ Mostrar tabla en un expander ===
    with st.expander("Ver tabla teórica de referencia de periodización (MD-6 → MD+1)"):
        st.dataframe(df_ref.drop(columns=["valor","Carga (1-10)","descripcion_output"]), hide_index=True)
        st.caption(
            "Esta tabla representa la **distribución teórica de cargas** dentro de un microciclo competitivo. "
            "Basada en los modelos de periodización táctica de Frade, Seirul-lo y estudios de Clemente et al. (2020)."
        )
    st.divider()
    return df_ref

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

