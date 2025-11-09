
import streamlit as st
import pandas as pd
from .plots_grupales import (plot_carga_semanal, plot_rpe_promedio, tabla_resumen, plot_monotonia_fatiga,plot_acwr)

def group_dashboard(df_filtrado: pd.DataFrame):
    """Panel grupal con gráficos y tablas agregadas."""

    #st.subheader(":material/group: Resumen grupal de cargas", divider=True)
    if df_filtrado.empty:
        st.info("No hay datos disponibles para el periodo seleccionado.")
        st.stop()

    st.divider()
    tabs = st.tabs([
        ":material/table_chart: Resumen tabular",
        ":material/monitor_weight: Carga y esfuerzo",
        ":material/trending_up: Índices de control",
        
    ])

    with tabs[0]:
        tabla_resumen(df_filtrado)
    with tabs[1]: 
        plot_carga_semanal(df_filtrado)
    with tabs[2]: 
        plot_rpe_promedio(df_filtrado)

    #--- Monotonía y fatiga ---
    #if {"semana", "monotonia", "fatiga_aguda"}.issubset(df_filtrado.columns):
    #plot_monotonia_fatiga(df_filtrado)

    #--- Relación aguda/crónica ---
    #if "acwr" in df_filtrado.columns:
    #plot_acwr(df_filtrado)

