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

PERIODIZACION = {
        "dia": ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD0", "MD+1", "+2",],
        "valor": [-6, -5, -4, -3, -2, -1, 0, 1, 2],
        "Carga (1-10)": [2, 4, 6, 8, 6, 5, 9, 3, 1],
        "Porcentaje estimado (%)": [20, 40, 60, 80, 60, 50, 100, 30, 0],
        "descripcion": [
            "Regenerativo: recuperación post-partido o compensación.",
            "Carga general: trabajo técnico y fuerza base.",
            "Carga media: componente técnico-táctico y fuerza específica.",
            "Carga alta: intensidad máxima y oposiciones tácticas.",
            "Media táctica: ajustes estratégicos y ritmo competitivo.",
            "Activación: coordinación, velocidad y preparación mental.",
            "Partido: máxima exigencia física, técnica y mental.",
            "baja intensidad, movilidad, recuperación activa.",
            "Descanso"
        ],
        "descripcion_output": [
            ":material/water_drop: Regenerativo: recuperación post-partido o compensación.",
            ":material/fitness_center: Carga general: trabajo técnico y fuerza base.",
            ":material/trending_up: Carga media: componente técnico-táctico y fuerza específica.",
            ":material/whatshot: Carga alta: intensidad máxima y oposiciones tácticas.",
            ":material/tune: Media táctica: ajustes estratégicos y ritmo competitivo.",
            ":material/bolt: Activación: coordinación, velocidad y preparación mental.",
            ":material/sports_soccer: Partido: máxima exigencia física, técnica y mental.",
            ":material/water_drop: Recuperación: baja intensidad, movilidad, recuperación activa.",
            ":material/sleep: Descanso"
        ]
}


def new_base_record(id_jugadora: str, username: str, tipo: str) -> dict:
    """Create a base record structure with defaults.

    tipo: 'checkIn' | 'checkOut'
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    return {
        "identificacion": id_jugadora,
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


