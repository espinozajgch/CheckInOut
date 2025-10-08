
import streamlit as st

def centered_text(text: str, font_size: int = 18, bold: bool = True):
    """
    Muestra un texto centrado dentro de un contenedor de Streamlit.

    Parameters
    ----------
    text : str
        Texto a mostrar centrado.
    font_size : int, optional
        Tamaño de la fuente (por defecto 18).
    bold : bool, optional
        Si True, el texto se muestra en negrita.
    """
    style = "font-weight:bold;" if bold else ""
    st.markdown(
        f"<div style='text-align:center; padding: 1rem; font-size:{font_size}px; {style}'>{text}</div>",
        unsafe_allow_html=True
    )

