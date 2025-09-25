from datetime import datetime
from typing import Dict, Tuple


def new_base_record(id_jugadora: str, nombre_jugadora: str, tipo: str) -> Dict:
    """Create a base record structure with defaults.

    tipo: 'checkIn' | 'checkOut'
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "id_jugadora": id_jugadora,
        "nombre_jugadora": nombre_jugadora,
        "fecha_hora": now,
        "tipo": tipo,
        "turno": "",
        # Check-in fields
        "periodizacion_tactica": "",
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
    }


def validate_checkin(record: Dict) -> Tuple[bool, str]:
    # Required 1..5
    for field in ["recuperacion", "fatiga", "sueno", "stress", "dolor"]:
        value = record.get(field)
        if value is None:
            return False, f"Completa el campo '{field}'."
        if not (1 <= int(value) <= 5):
            return False, f"El campo '{field}' debe estar entre 1 y 5."
    # Dolor parts if dolor > 1
    if int(record.get("dolor", 0)) > 1:
        if not record.get("partes_cuerpo_dolor"):
            return False, "Selecciona al menos una parte del cuerpo con dolor."
    return True, ""

essential_checkout_fields = ("minutos_sesion", "rpe")

