import datetime

# Diccionario de equivalencias
MAP_POSICIONES = {
    "POR": "Portera",
    "DEF": "Defensa",
    "MC": "Centro",
    "DEL": "Delantera"
}

# === Diccionario para traducir días ===
DIAS_SEMANA = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

def new_base_record(id_jugadora: str, username: str, tipo: str) -> dict:
    """Create a base record structure with defaults.

    tipo: 'checkIn' | 'checkOut'
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    return {
        "id_jugadora": id_jugadora,
        #"nombre": nombre_jugadora,
        "fecha_sesion": now,
        "tipo": tipo,
        "turno": "",
        # Check-in fields
        "periodizacion_tactica": "",
        "id_tipo_estimulo": "",
        "id_tipo_readaptacion": "",
        "recuperacion": None,
        "fatiga": None,
        "sueno": None,
        "stress": None,
        "dolor": None,
        "partes_cuerpo_dolor": [],
        # Check-out fields
        "minutos_sesion": None,
        "rpe": None,
        "ua": None,
        # Extras
        "en_periodo": False,
        "observacion": "",
        "fecha_hora_registro": datetime.datetime.now().isoformat(),
        "usuario": username
    }


