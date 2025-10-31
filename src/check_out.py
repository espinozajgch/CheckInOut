import streamlit as st
import pandas as pd

def checkout_form(record: dict) -> tuple[dict, bool, str]:
    
    with st.container():
        st.markdown("#### **Check-out (post-entrenamiento)**")

        col1, col2, col3,_, _ = st.columns([.5, .5, .5, 1,1])
        with col1:
            record["minutos_sesion"] = st.number_input("Minutos de la sesión", min_value=1, step=1)
        with col2:
            record["rpe"] = st.number_input("RPE (1-10)", min_value=1, max_value=10, step=1)
        with col3:
            # Auto-calc UA
            minutos = int(record.get("minutos_sesion") or 0)
            rpe = int(record.get("rpe") or 0)
            record["ua"] = int(rpe * minutos) if minutos > 0 and rpe > 0 else None
            st.metric("UA (RPE x minutos)", value=record["ua"] if record["ua"] is not None else "-")

        is_valid, msg = validate_checkout(record)
        return record, is_valid, msg

def validate_checkout(record: dict) -> tuple[bool, str]:
    # Minutes > 0
    minutos = record.get("minutos_sesion")
    if minutos is None or int(minutos) <= 0:
        return False, "Los minutos de la sesión deben ser un entero positivo."
    # RPE 1..10
    rpe = record.get("rpe")
    if rpe is None or not (1 <= int(rpe) <= 10):
        return False, "El RPE debe estar entre 1 y 10."
    # UA computed
    ua = record.get("ua")
    if ua is None:
        return False, "UA no calculado."
    return True, ""