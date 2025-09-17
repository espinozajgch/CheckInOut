import json
import os
from io import BytesIO
from typing import Optional, Tuple, List, Dict

import pandas as pd

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(BASE_DIR, "data")
JUGADORAS_XLSX = os.path.join(DATA_DIR, "jugadoras.xlsx")
PARTES_CUERPO_XLSX = os.path.join(DATA_DIR, "partes_cuerpo.xlsx")
REGISTROS_JSONL = os.path.join(DATA_DIR, "registros.jsonl")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_jugadoras() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Load jugadoras Excel. Expects columns: id_jugadora, nombre_jugadora

    Returns (df, error_msg). If error_msg is not None, df will be None.
    """
    _ensure_data_dir()
    if not os.path.exists(JUGADORAS_XLSX):
        return None, f"No se encontró {JUGADORAS_XLSX}. Descarga y coloca el archivo."
    try:
        df = pd.read_excel(JUGADORAS_XLSX)
        expected = {"id_jugadora", "nombre_jugadora"}
        if not expected.issubset(df.columns.astype(str)):
            return None, f"Las columnas deben ser: {sorted(list(expected))}."
        return df, None
    except Exception as e:
        return None, f"Error leyendo jugadoras.xlsx: {e}"


def load_partes_cuerpo() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Load partes del cuerpo Excel. Expects column: parte

    Returns (df, error_msg). If error_msg is not None, df will be None.
    """
    _ensure_data_dir()
    if not os.path.exists(PARTES_CUERPO_XLSX):
        return None, f"No se encontró {PARTES_CUERPO_XLSX}. Descarga y coloca el archivo."
    try:
        df = pd.read_excel(PARTES_CUERPO_XLSX)
        expected = {"parte"}
        if not expected.issubset(df.columns.astype(str)):
            return None, f"Las columnas deben incluir: {sorted(list(expected))}."
        return df, None
    except Exception as e:
        return None, f"Error leyendo partes_cuerpo.xlsx: {e}"


def get_template_bytes(template_type: str) -> bytes:
    """Return Excel bytes for templates.

    template_type: 'jugadoras' or 'partes_cuerpo'
    """
    if template_type == "jugadoras":
        df = pd.DataFrame([
            {"id_jugadora": "1", "nombre_jugadora": "Jugador/a 1"},
            {"id_jugadora": "2", "nombre_jugadora": "Jugador/a 2"},
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


def _read_all_records() -> List[Dict]:
    """Read all JSONL records as a list of dicts. Missing file -> empty list."""
    _ensure_data_dir()
    records: List[Dict] = []
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


def _write_all_records(records: List[Dict]) -> None:
    """Overwrite the JSONL file with the provided records list."""
    _ensure_data_dir()
    with open(REGISTROS_JSONL, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _date_only(ts: str) -> str:
    """Extract YYYY-MM-DD from timestamp string like YYYY-MM-DDTHH:MM:SS."""
    return (ts or "").split("T")[0]


def upsert_jsonl(record: Dict) -> None:
    """Upsert a record by (id_jugadora, fecha YYYY-MM-DD, turno).

    - Si existe un registro del mismo día, misma jugadora y mismo turno, se fusiona
      prefiriendo los valores no nulos del nuevo registro.
    - Si no existe, se agrega como nuevo.
    - Tras fusionar, 'tipo' = 'checkOut' si hay campos de checkout presentes
      (minutos_sesion, rpe, ua); de lo contrario 'checkIn'.
    """
    records = _read_all_records()
    key_id = record.get("id_jugadora")
    key_day = _date_only(record.get("fecha_hora", ""))
    key_turno = (record.get("turno") or "").strip()

    idx_to_update = None
    for idx, rec in enumerate(records):
        rec_turno = (rec.get("turno") or "").strip()
        if (
            rec.get("id_jugadora") == key_id
            and _date_only(rec.get("fecha_hora", "")) == key_day
            and rec_turno == key_turno
        ):
            idx_to_update = idx
            break

    def merge_records(old: Dict, new: Dict) -> Dict:
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


def get_record_for_player_day(id_jugadora: str, fecha_hora: str) -> Optional[Dict]:
    """[DEPRECATED] Usa get_record_for_player_day_turno cuando haya turno.

    Devuelve el primer registro para la jugadora y el día dado (ignora turno).
    """
    records = _read_all_records()
    target_day = _date_only(fecha_hora or "")
    for rec in records:
        if rec.get("id_jugadora") == id_jugadora and _date_only(rec.get("fecha_hora", "")) == target_day:
            return rec
    return None


def get_record_for_player_day_turno(id_jugadora: str, fecha_hora: str, turno: str) -> Optional[Dict]:
    """Devuelve el primer registro para (jugadora, día, turno)."""
    records = _read_all_records()
    target_day = _date_only(fecha_hora or "")
    turno = (turno or "").strip()
    for rec in records:
        if (
            rec.get("id_jugadora") == id_jugadora
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
