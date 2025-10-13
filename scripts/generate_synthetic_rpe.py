import random
from datetime import datetime, timedelta, time
import os
import shutil
import pandas as pd
import sys

# Ensure project root is on sys.path so that 'src' package is importable when running this script directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.io_files import (
    upsert_jsonl,
    get_record_for_player_day_turno,
    DATA_DIR,
    JUGADORAS_XLSX,
    REGISTROS_JSONL,
)
from src.schema import new_base_record, validate_checkout


def load_players():
    if not os.path.exists(JUGADORAS_XLSX):
        raise FileNotFoundError(f"No se encontró el archivo de jugadoras: {JUGADORAS_XLSX}")
    df = pd.read_excel(JUGADORAS_XLSX)
    if not {"identificacion", "nombre"}.issubset(df.columns.astype(str)):
        raise ValueError("El archivo jugadoras.xlsx debe tener las columnas: id_jugadora, nombre_jugadora")
    return df


def backup_registros():
    if os.path.exists(REGISTROS_JSONL):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"registros.backup_{ts}.jsonl")
        shutil.copy(REGISTROS_JSONL, backup_path)
        return backup_path
    return None


def date_range_days(end_inclusive: datetime, days: int):
    start = end_inclusive - timedelta(days=days - 1)
    current = start
    while current <= end_inclusive:
        yield current
        current += timedelta(days=1)


def random_session_time():
    # Typical post-training times between 17:00 and 21:00
    hour = random.randint(17, 21)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return time(hour, minute, second)


def should_train_on(day: datetime) -> bool:
    # Higher chance on weekdays, lower on weekends
    weekday = day.weekday()  # 0 Mon .. 6 Sun
    if weekday < 5:  # Monday-Friday
        return random.random() < 0.6
    else:  # Saturday-Sunday
        return random.random() < 0.35


def generate_rpe_for_range(days: int = 30, seed: int = 42) -> None:
    random.seed(seed)

    players = load_players()
    end_day = datetime.now().date() - timedelta(days=1)  # up to yesterday
    end_dt = datetime.combine(end_day, time(12, 0, 0))

    backup_path = backup_registros()
    if backup_path:
        print(f"Backup creado: {backup_path}")

    total_created = 0
    skipped_existing = 0

    turnos = ["Turno 1", "Turno 2", "Turno 3"]

    for d in date_range_days(end_dt, days):
        # Decide if there is a training session on this day
        if not should_train_on(d):
            continue

        for _, row in players.iterrows():
            jug_id = str(row["identificacion"])
            jug_name = str(row["nombre"])

            # Randomly choose a turno per player per day
            turno = random.choice(turnos)

            # Build a timestamp with a plausible session end time
            t = random_session_time()
            fecha_hora = datetime.combine(d.date(), t).strftime("%Y-%m-%dT%H:%M:%S")

            # Skip if a record already exists for this player/day/turno
            existing = get_record_for_player_day_turno(jug_id, fecha_hora, turno)
            if existing is not None:
                skipped_existing += 1
                continue

            # Create a base record and populate checkout fields
            record = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkOut")
            record["fecha_hora"] = fecha_hora
            record["turno"] = turno

            # Generate realistic minutes and RPE
            minutos = int(random.gauss(85, 20))  # around 85 min, sd=20
            minutos = max(40, min(minutos, 130))
            rpe = int(round(random.gauss(5.5, 1.5)))  # average intensity 5-6
            rpe = max(1, min(rpe, 10))

            record["minutos_sesion"] = minutos
            record["rpe"] = rpe
            record["ua"] = int(minutos * rpe)

            ok, msg = validate_checkout(record)
            if not ok:
                print(f"Registro inválido para {jug_name} {fecha_hora} ({turno}): {msg}")
                continue

            upsert_jsonl(record)
            total_created += 1

    print(f"Registros creados: {total_created}")
    print(f"Registros omitidos por existir: {skipped_existing}")
    print(f"Archivo destino: {REGISTROS_JSONL}")


if __name__ == "__main__":
    # Default: generate last 30 days. Adjust via code if needed.
    generate_rpe_for_range(days=30, seed=42)
