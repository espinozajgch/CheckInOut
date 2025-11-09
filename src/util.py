import streamlit as st
import math
import re
import numpy as np
import requests
import pandas as pd
import datetime
from urllib.parse import urlparse, urlunparse

import unicodedata
import datetime
from dateutil.relativedelta import relativedelta  # pip install python-dateutil

def normalize_text(s):
    """Limpia texto eliminando tildes, espacios invisibles y normalizando Unicode."""
    if not isinstance(s, str):
        return ""
    s = s.strip().upper()
    s = unicodedata.normalize("NFKC", s)  # Normaliza forma Unicode
    return s


def get_photo(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Verifica si hubo un error (por ejemplo, 404 o 500)
    except requests.exceptions.RequestException:
        response = None  # Si hay un error, no asignamos nada a response

    return response

def clean_df(records):
    columnas_excluir = [
        "wellness_score"
    ]
    
    # --- eliminar columnas si existen ---
    df_filtrado = records.drop(columns=[col for col in columnas_excluir if col in records.columns])

    orden = ["fecha_lesion", "nombre_jugadora", "posicion", "plantel" ,"id_lesion", "lugar", "segmento", "zona_cuerpo", "zona_especifica", "lateralidad", "tipo_lesion", "tipo_especifico", "gravedad", "tipo_tratamiento", "personal_reporta", "estado_lesion", "sesiones"]
    
    # Solo mantener columnas que realmente existen
    orden_existentes = [c for c in orden if c in df_filtrado.columns]

    df_filtrado = df_filtrado[orden_existentes + [c for c in df_filtrado.columns if c not in orden_existentes]]
        
    #df_filtrado = df_filtrado[orden + [c for c in df_filtrado.columns if c not in orden]]

    df_filtrado = df_filtrado.sort_values("fecha_hora_registro", ascending=False)
    df_filtrado.reset_index(drop=True, inplace=True)
    df_filtrado.index = df_filtrado.index + 1
    return df_filtrado

def calcular_edad(fecha_nac):
    try:
        # Si viene como string -> convertir
        if isinstance(fecha_nac, str):
            fnac = datetime.datetime.strptime(fecha_nac, "%Y-%m-%d").date()
        elif isinstance(fecha_nac, datetime.date):
            fnac = fecha_nac
        else:
            return "N/A", None

        hoy = datetime.date.today()
        diff = relativedelta(hoy, fnac)

        edad_anos = diff.years
        edad_meses = diff.months

        edad_texto = f"{edad_anos} años y {edad_meses} meses"
        return edad_texto, fnac

    except Exception as e:
        return f"Error: {e}", None

def clean_image_url(url: str) -> str:
    """
    Limpia y normaliza URLs de imágenes:
    - Si es de Google Drive, la convierte a formato directo de descarga/visualización.
    - Si tiene parámetros (como '?size=...' o '&lossy=1'), los elimina.
    - Si ya es una URL limpia, la devuelve igual.
    """

    if not url or not isinstance(url, str):
        return ""

    # --- 1️⃣ Caso Google Drive ---
    if "drive.google.com" in url:
        # Caso A: /file/d/<ID>/view?usp=sharing
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?id={file_id}"

        # Caso B: open?id=<ID>
        match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?id={file_id}"

        # Si no encuentra ID, devuelve sin cambios
        return url

    # --- 2️⃣ Caso URLs con parámetros (ej. cdn.resfu.com) ---
    parsed = urlparse(url)
    # Elimina los parámetros de consulta (?size=...&lossy=...)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    return clean_url

def get_drive_direct_url(url: str) -> str:
    """
    Convierte un enlace de Google Drive en un enlace directo para visualizar o descargar la imagen.

    Args:
        url (str): Enlace de Google Drive (por ejemplo, 'https://drive.google.com/file/d/.../view?usp=sharing')

    Returns:
        str: Enlace directo usable en st.image o <img src="...">
    """
    if not url:
        return ""

    # Detectar si contiene el patrón de ID
    if "drive.google.com" not in url:
        raise ValueError("La URL no parece ser de Google Drive")

    # Buscar el ID del archivo
    import re
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError("No se pudo extraer el ID del archivo de la URL")

    file_id = match.group(1)
    return f"https://drive.google.com/uc?export=view&id={file_id}"

def parse_fecha(value):
    """
    Convierte un valor en objeto datetime.date de forma segura.

    Acepta:
        - str en formato ISO ('YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS')
        - datetime.date
        - datetime.datetime
        - None o vacío

    Devuelve:
        datetime.date | None
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None

    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        # Ya es un objeto date
        return value

    if isinstance(value, datetime.datetime):
        # Extraer solo la parte de fecha
        return value.date()

    if isinstance(value, str):
        try:
            # Intentar formato ISO estándar
            return datetime.date.fromisoformat(value.split("T")[0])
        except Exception:
            try:
                # Intentar otros formatos comunes (por compatibilidad)
                return datetime.datetime.strptime(value, "%Y-%m-%d").date()
            except Exception:
                return None

    # Si no es ningún tipo compatible
    return None

def is_valid(value):
    """Devuelve True si el valor no es None, vacío ni NaN."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (float, np.floating)) and math.isnan(value):
        return False
    if pd.isna(value):  # cubre np.nan, pd.NaT y similares
        return False
    return True

def to_date(value):
    """Convierte una cadena o datetime a date (YYYY-MM-DD)."""
    if isinstance(value, datetime.date):
        return value
    try:
        return pd.to_datetime(value, errors="coerce").date()
    except Exception:
        return None
