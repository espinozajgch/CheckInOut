import json
import os
from io import BytesIO

import pandas as pd

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(BASE_DIR, "data")
JUGADORAS_JSON = os.path.join(DATA_DIR, "jugadoras.jsonl")
PARTES_CUERPO_JSON = os.path.join(DATA_DIR, "partes_cuerpo.jsonl")
REGISTROS_JSONL = os.path.join(DATA_DIR, "registros.jsonl")
COMPETICIONES_JSONL = os.path.join(DATA_DIR, "competiciones.jsonl")
USERS_FILE = os.path.join(DATA_DIR, "users.jsonl")

def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

def load_users():
    """Carga usuarios desde USERS_FILE en formato JSON estándar (lista) o JSONL (una línea por objeto).
    Devuelve siempre una lista de diccionarios.
    """
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            return []

        first_char = text.lstrip()[:1]

        # --- Caso 1: JSON estándar (lista de objetos) ---
        if first_char == "[":
            data = json.loads(text)
            if not isinstance(data, list):
                st.error("El archivo de usuarios no contiene una lista JSON válida.")
                return []
            return [u for u in data if isinstance(u, dict)]

        # --- Caso 2: JSONL (una línea por usuario) ---
        elif first_char == "{":
            users = []
            for i, line in enumerate(text.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        users.append(obj)
                except json.JSONDecodeError as e:
                    st.error(f"Error de JSON en la línea {i} de '{USERS_FILE}': {e}")
                    return []
            return users

        else:
            st.error("Formato de archivo de usuarios no reconocido (ni lista JSON ni JSONL).")
            return []

    except FileNotFoundError:
        st.error("Archivo de usuarios no encontrado.")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error al leer el archivo de usuarios: {e}")
        return []
    except Exception as e:
        st.error(f"Error inesperado al cargar usuarios: {e}")
        return []

def load_competiciones() -> tuple[pd.DataFrame | None, str | None]:
    """
    Carga jugadoras desde archivo JSON. Se esperan las claves: id_jugadora, nombre_jugadora

    Returns:
        tuple: (DataFrame o None, mensaje de error o None)
    """
    _ensure_data_dir()
    if not os.path.exists(COMPETICIONES_JSONL):
        return None, f"No se encontró {COMPETICIONES_JSONL}. Descarga y coloca el archivo."

    try:
        with open(COMPETICIONES_JSONL, "r", encoding="utf-8") as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        #df = df[df["activo"] == 1]
        df = df.sort_values("nombre")

        return df, None

    except Exception as e:
        return None, f"Error leyendo jugadoras.json: {e}"

def load_jugadoras() -> tuple[pd.DataFrame | None, str | None]:
    """
    Carga jugadoras desde archivo JSON. Se esperan las claves: id_jugadora, nombre_jugadora

    Returns:
        tuple: (DataFrame o None, mensaje de error o None)
    """
    _ensure_data_dir()
    if not os.path.exists(JUGADORAS_JSON):
        return None, f"No se encontró {JUGADORAS_JSON}. Descarga y coloca el archivo."

    try:
        with open(JUGADORAS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        df = df[df["activo"] == 1]
        df = df.sort_values("nombre")

        return df, None

    except Exception as e:
        return None, f"Error leyendo jugadoras.json: {e}"

def load_partes_json() -> tuple[pd.DataFrame | None, str | None]:
    try:
        with open(PARTES_CUERPO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Verifica que el formato sea tipo: {"parte": [ ... ]}
        if not isinstance(data, dict) or "parte" not in data:
            return None, "Formato inválido: se esperaba una clave 'parte' con lista de valores."

        partes = data["parte"]
        if not isinstance(partes, list) or not all(isinstance(p, str) for p in partes):
            return None, "Los valores bajo 'parte' deben ser una lista de strings."

        # Convertimos a DataFrame como espera la app
        df = pd.DataFrame({"parte": partes})
        return df, None

    except Exception as e:
        return None, f"Error al cargar el archivo: {e}"

def get_template_bytes(template_type: str) -> bytes:
    """Return Excel bytes for templates.

    template_type: 'jugadoras' or 'partes_cuerpo'
    """
    if template_type == "jugadoras":
        df = pd.DataFrame([
            {"identificacion": "1", "nombre": "Jugador/a 1"},
            {"identificacion": "2", "nombre": "Jugador/a 2"},
        ])
    elif template_type == "partes_cuerpo":
        df = pd.DataFrame([
            {"parte": "Cuello"},
            {"parte": "Hombro"},
            {"parte": "Brazo"},
            {"parte": "Espalda"},
            {"parte": "Cadera"},
            {"parte": "Muslo"},
            {"parte": "Rodilla"},
            {"parte": "Pantorrilla"},
            {"parte": "Tobillo"},
            {"parte": "Pie"},
        ])
    else:
        df = pd.DataFrame()

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.read()

def append_jsonl(record: dict) -> None:
    """Append a dict as one line of JSON to the registros.jsonl file."""
    _ensure_data_dir()
    # Ensure file exists
    if not os.path.exists(REGISTROS_JSONL):
        with open(REGISTROS_JSONL, "w", encoding="utf-8") as f:
            pass
    with open(REGISTROS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def _read_all_records() -> list[dict]:
    """Read all JSONL records as a list of dicts. Missing file -> empty list."""
    _ensure_data_dir()
    records: list[dict] = []
    if not os.path.exists(REGISTROS_JSONL):
        return records
    with open(REGISTROS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                # Skip malformed lines
                continue
    return records

def _write_all_records(records: list[dict]) -> None:
    """Overwrite the JSONL file with the provided records list."""
    _ensure_data_dir()
    with open(REGISTROS_JSONL, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _date_only(ts: str) -> str:
    """Extract YYYY-MM-DD from timestamp string like YYYY-MM-DDTHH:MM:SS."""
    return (ts or "").split("T")[0]

def upsert_jsonl(record: dict) -> None:
    """Upsert a record by (id_jugadora, fecha YYYY-MM-DD, turno).

    - Si existe un registro del mismo día, misma jugadora y mismo turno, se fusiona
      prefiriendo los valores no nulos del nuevo registro.
    - Si no existe, se agrega como nuevo.
    - Tras fusionar, 'tipo' = 'checkOut' si hay campos de checkout presentes
      (minutos_sesion, rpe, ua); de lo contrario 'checkIn'.
    """
    records = _read_all_records()
    key_id = record.get("identificacion")
    key_day = _date_only(record.get("fecha_hora", ""))
    key_turno = (record.get("turno") or "").strip()

    idx_to_update = None
    for idx, rec in enumerate(records):
        rec_turno = (rec.get("turno") or "").strip()
        if (
            rec.get("identificacion") == key_id
            and _date_only(rec.get("fecha_hora", "")) == key_day
            and rec_turno == key_turno
        ):
            idx_to_update = idx
            break

    def merge_records(old: dict, new: dict) -> dict:
        merged = dict(old)
        for k, v in new.items():
            # Special handling: do not overwrite 'en_periodo' to False; only set True explicitly
            if k == "en_periodo":
                if v is True:
                    merged[k] = True
                # if v is False or None, keep previous value
                continue
            # Prefer new non-None values, but avoid overwriting with empty strings/lists
            if v is not None:
                if isinstance(v, str):
                    if v != "":
                        merged[k] = v
                elif isinstance(v, list):
                    if len(v) > 0:
                        merged[k] = v
                else:
                    merged[k] = v
        # Determine tipo after merge based on presence of checkout fields
        has_checkout = any(
            merged.get(x) is not None for x in ("minutos_sesion", "rpe", "ua")
        )
        merged["tipo"] = "checkOut" if has_checkout else "checkIn"
        return merged

    if idx_to_update is None:
        # No existing -> append
        records.append(record)
    else:
        # Merge into existing record
        records[idx_to_update] = merge_records(records[idx_to_update], record)

    _write_all_records(records)

def get_record_for_player_day(id_jugadora: str, fecha_hora: str):
    """[DEPRECATED] Usa get_record_for_player_day_turno cuando haya turno.

    Devuelve el primer registro para la jugadora y el día dado (ignora turno).
    """
    records = _read_all_records()
    target_day = _date_only(fecha_hora or "")
    for rec in records:
        if rec.get("identificacion") == id_jugadora and _date_only(rec.get("fecha_hora", "")) == target_day:
            return rec
    return None

def get_record_for_player_day_turno(id_jugadora: str, fecha_hora: str, turno: str):
    """Devuelve el primer registro para (jugadora, día, turno)."""
    records = _read_all_records()
    target_day = _date_only(fecha_hora or "")
    turno = (turno or "").strip()
    for rec in records:
        if (
            rec.get("identificacion") == id_jugadora
            and _date_only(rec.get("fecha_hora", "")) == target_day
            and (rec.get("turno") or "").strip() == turno
        ):
            return rec
    return None

def get_records_df() -> pd.DataFrame:
    """Return all registros as a pandas DataFrame. If none, returns empty DF.

    Adds helper columns:
    - fecha (datetime)
    - fecha_dia (date)
    """
    recs = _read_all_records()
    if not recs:
        return pd.DataFrame()
    df = pd.DataFrame(recs)
    # Parse fecha_hora
    try:
        df["fecha"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
        df["fecha_dia"] = df["fecha"].dt.date
    except Exception:
        pass
    return df
