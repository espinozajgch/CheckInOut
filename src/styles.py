"""
🎨 Estilos y paletas globales del proyecto CheckInOut.
Incluye colores corporativos, escalas semafóricas y paletas de interpretación Wellness.
"""

# --- Colores corporativos ---
BRAND_PRIMARY = "#1565C0"
BRAND_SECONDARY = "#E64A19"
BRAND_TEXT = "#212121"
BRAND_BACKGROUND = "#F5F5F5"

# --- Escalas semafóricas genéricas ---
SEMAFORO = {
    "rojo": "#E53935",
    "naranja": "#FB8C00",
    "amarillo": "#FDD835",
    "verde_claro": "#2ECC71",
    "verde_oscuro": "#27AE60",
    "gris": "#BDBDBD"
}

# --- Escalas de interpretación WELLNESS ---
WELLNESS_COLOR_NORMAL = {
    1: "#E74C3C",  # rojo
    2: "#E67E22",  # naranja
    3: "#F1C40F",  # amarillo
    4: "#2ECC71",  # verde claro
    5: "#27AE60",  # verde oscuro
}

WELLNESS_COLOR_INVERTIDO = {
    1: "#27AE60",  # verde oscuro
    2: "#2ECC71",  # verde claro
    3: "#F1C40F",  # amarillo
    4: "#E67E22",  # naranja
    5: "#E74C3C",  # rojo
}

# --- Funciones utilitarias ---
def get_color_wellness(valor: float | int | None, variable: str) -> str:
    """
    Devuelve el color correspondiente para una variable Wellness (1–5)
    según la escala normal o invertida.
    """
    if valor is None:
        return WELLNESS_COLOR_NORMAL[3]  # neutro
    try:
        v = int(round(float(valor)))
    except Exception:
        v = 3
    cmap = WELLNESS_COLOR_INVERTIDO if variable in ["Estrés", "Dolor"] else WELLNESS_COLOR_NORMAL
    return cmap.get(v, WELLNESS_COLOR_NORMAL[3])
