import random
from datetime import datetime, timedelta, time
import os
import shutil
import pandas as pd

from .io_files import (
    upsert_jsonl,
    get_record_for_player_day_turno,
    DATA_DIR,
    JUGADORAS_XLSX,
    REGISTROS_JSONL,
    PARTES_CUERPO_XLSX,
)
from .schema import new_base_record, validate_checkout


def _load_players():
    if not os.path.exists(JUGADORAS_XLSX):
        raise FileNotFoundError(f"No se encontró el archivo de jugadoras: {JUGADORAS_XLSX}")
    df = pd.read_excel(JUGADORAS_XLSX)
    if not {"id_jugadora", "nombre_jugadora"}.issubset(df.columns.astype(str)):
        raise ValueError("El archivo jugadoras.xlsx debe tener las columnas: id_jugadora, nombre_jugadora")
    return df


def _backup_registros() -> str | None:
    if os.path.exists(REGISTROS_JSONL):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"registros.backup_{ts}.jsonl")
        shutil.copy(REGISTROS_JSONL, backup_path)
        return backup_path
    return None


def _date_range_days(end_inclusive: datetime, days: int):
    start = end_inclusive - timedelta(days=days - 1)
    current = start
    while current <= end_inclusive:
        yield current
        current += timedelta(days=1)


def _random_session_time():
    hour = random.randint(17, 21)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return time(hour, minute, second)


def _should_train_on(day: datetime) -> bool:
    weekday = day.weekday()  # 0..6
    if weekday < 5:
        return random.random() < 0.6
    else:
        return random.random() < 0.35


def generate_synthetic_rpe(days: int = 30, seed: int = 42) -> dict:
    """Genera datos sintéticos de RPE (check-out) para los últimos N días.

    Devuelve un resumen con backups y contadores para mostrar en UI.
    """
    random.seed(seed)

    players = _load_players()
    end_day = datetime.now().date() - timedelta(days=1)
    end_dt = datetime.combine(end_day, time(12, 0, 0))

    backup_path = _backup_registros()

    total_created = 0
    skipped_existing = 0

    turnos = ["Turno 1", "Turno 2", "Turno 3"]

    for d in _date_range_days(end_dt, days):
        if not _should_train_on(d):
            continue
        for _, row in players.iterrows():
            jug_id = str(row["id_jugadora"])
            jug_name = str(row["nombre_jugadora"])
            turno = random.choice(turnos)
            t = _random_session_time()
            fecha_hora = datetime.combine(d.date(), t).strftime("%Y-%m-%dT%H:%M:%S")
            existing = get_record_for_player_day_turno(jug_id, fecha_hora, turno)
            if existing is not None:
                skipped_existing += 1
                continue
            record = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkOut")
            record["fecha_hora"] = fecha_hora
            record["turno"] = turno
            minutos = int(random.gauss(85, 20))
            minutos = max(40, min(minutos, 130))
            rpe = int(round(random.gauss(5.5, 1.5)))
            rpe = max(1, min(rpe, 10))
            record["minutos_sesion"] = minutos
            record["rpe"] = rpe
            record["ua"] = int(minutos * rpe)
            ok, msg = validate_checkout(record)
            if not ok:
                continue
            upsert_jsonl(record)
            total_created += 1

    return {
        "backup": backup_path,
        "created": total_created,
        "skipped": skipped_existing,
        "target": REGISTROS_JSONL,
        "days": days,
    }


def generate_synthetic_full(days: int = 30, seed: int = 777) -> dict:
    """Genera datos completos (Check-in y Check-out) para TODAS las jugadoras
    para los últimos N días, asignando una periodización táctica que avanza
    cronológicamente día a día. Se usa un único turno por jugadora y día.

    - Check-in: 08:00–11:00 aprox, wellness 1..5 + periodización_tactica progresiva
    - Check-out: 17:00–21:00 aprox, minutos, RPE y UA = minutos * RPE
    - Upsert por (jugadora, día, turno) para fusionar ambos registros
    """
    import math

    random.seed(seed)

    players = _load_players()
    # Rango: desde ayer hacia atrás N-1 días (incluye ayer)
    end_day = datetime.now().date() - timedelta(days=1)
    end_dt = datetime.combine(end_day, time(12, 0, 0))

    backup_path = _backup_registros()

    turnos = ["Turno 1", "Turno 2", "Turno 3"]
    total_upserts = 0

    # Generar una secuencia cronológica de PT por día del rango: -6..+6 cíclico
    # Comenzamos en -6 y vamos incrementando hasta +6, luego reiniciamos en -6
    def pt_sequence(n: int):
        vals = []
        cur = -6
        for _ in range(n):
            vals.append(cur)
            cur += 1
            if cur > 6:
                cur = -6
        return vals

    days_list = list(_date_range_days(end_dt, days))
    day_pts = pt_sequence(len(days_list))

    created_ci = 0
    created_co = 0

    for idx, d in enumerate(days_list):
        pt_val = day_pts[idx]
        for _, row in players.iterrows():
            jug_id = str(row["id_jugadora"])
            jug_name = str(row["nombre_jugadora"])
            turno = random.choice(turnos)

            # --- Check-in ---
            # Hora de mañana 07:00–11:59
            h_in = random.randint(7, 11)
            m_in = random.randint(0, 59)
            s_in = random.randint(0, 59)
            fecha_ci = datetime.combine(d.date(), time(h_in, m_in, s_in)).strftime("%Y-%m-%dT%H:%M:%S")

            rec_in = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkIn")
            rec_in["fecha_hora"] = fecha_ci
            rec_in["turno"] = turno
            rec_in["periodizacion_tactica"] = pt_val

            # Wellness sintético relativamente realista
            def clamp(v: int, lo: int = 1, hi: int = 5) -> int:
                return max(lo, min(hi, v))

            base = random.choice([2, 3])  # alrededor de 2-3 para mantener equilibrio
            rec_in["recuperacion"] = clamp(base + random.choice([-1, 0, 0, 1]))
            rec_in["fatiga"] = clamp(6 - rec_in["recuperacion"] + random.choice([-1, 0, 0, 1]))
            rec_in["sueno"] = clamp(base + random.choice([-1, 0, 1]))
            rec_in["stress"] = clamp(base + random.choice([-1, 0, 1]))
            # Dolor más bajo en general
            rec_in["dolor"] = clamp(random.choices([1, 2, 3, 4], weights=[60, 25, 12, 3])[0])
            # Partes con dolor si aplica (si existe catálogo)
            try:
                if rec_in["dolor"] > 1 and os.path.exists(PARTES_CUERPO_XLSX):
                    partes_df = pd.read_excel(PARTES_CUERPO_XLSX)
                    partes_opts = partes_df["parte"].dropna().astype(str).tolist() if "parte" in partes_df.columns else []
                else:
                    partes_opts = []
            except Exception:
                partes_opts = []
            if rec_in["dolor"] > 1 and partes_opts:
                k = random.randint(1, min(2, len(partes_opts)))
                rec_in["partes_cuerpo_dolor"] = random.sample(partes_opts, k)
            else:
                rec_in["partes_cuerpo_dolor"] = []
            rec_in["en_periodo"] = (random.random() < 0.15)
            rec_in["observacion"] = ""

            upsert_jsonl(rec_in)
            created_ci += 1

            # --- Check-out ---
            # Hora tarde 17:00–21:59
            h_out = random.randint(17, 21)
            m_out = random.randint(0, 59)
            s_out = random.randint(0, 59)
            fecha_co = datetime.combine(d.date(), time(h_out, m_out, s_out)).strftime("%Y-%m-%dT%H:%M:%S")

            rec_out = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkOut")
            rec_out["fecha_hora"] = fecha_co
            rec_out["turno"] = turno
            rec_out["periodizacion_tactica"] = pt_val

            minutos = int(random.gauss(85, 20))
            minutos = max(40, min(minutos, 130))
            rpe = int(round(random.gauss(5.5, 1.5)))
            rpe = max(1, min(rpe, 10))
            rec_out["minutos_sesion"] = minutos
            rec_out["rpe"] = rpe
            rec_out["ua"] = int(minutos * rpe)

            ok, _ = validate_checkout(rec_out)
            if ok:
                upsert_jsonl(rec_out)
                created_co += 1

    total_upserts = created_ci + created_co

    return {
        "backup": backup_path,
        "created_checkin": created_ci,
        "created_checkout": created_co,
        "total_upserts": total_upserts,
        "target": REGISTROS_JSONL,
        "days": days,
    }


def generate_synthetic_checkin(days: int = 30, seed: int = 123) -> dict:
    """Genera datos sintéticos de Check-in para los últimos N días.

    Crea/actualiza registros con campos de check-in: recuperacion, fatiga, sueno, stress, dolor,
    periodizacion_tactica, en_periodo, observacion y partes_cuerpo_dolor (si dolor>1).
    Respeta (jugadora, día, turno) y hace upsert sin borrar check-out existente.
    """
    random.seed(seed)

    # Jugadoras y partes del cuerpo
    players = _load_players()
    partes_df = None
    try:
        if os.path.exists(PARTES_CUERPO_XLSX):
            partes_df = pd.read_excel(PARTES_CUERPO_XLSX)
    except Exception:
        partes_df = None
    partes_opts = (
        partes_df["parte"].dropna().astype(str).tolist() if (isinstance(partes_df, pd.DataFrame) and "parte" in partes_df.columns) else []
    )

    end_day = datetime.now().date() - timedelta(days=1)
    end_dt = datetime.combine(end_day, time(8, 0, 0))

    backup_path = _backup_registros()

    total_created = 0
    skipped_existing = 0

    turnos = ["Turno 1", "Turno 2", "Turno 3"]

    for d in _date_range_days(end_dt, days):
        if not _should_train_on(d):
            continue
        for _, row in players.iterrows():
            jug_id = str(row["id_jugadora"])
            jug_name = str(row["nombre_jugadora"])
            turno = random.choice(turnos)
            # Hora de la mañana típica de check-in
            h = random.randint(7, 11)
            m = random.randint(0, 59)
            s = random.randint(0, 59)
            fecha_hora = datetime.combine(d.date(), time(h, m, s)).strftime("%Y-%m-%dT%H:%M:%S")

            # Si ya existe un registro ese día/turno, haremos merge (upsert) igualmente; no lo saltamos.
            # Creamos el registro base y rellenamos campos de check-in.
            rec = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkIn")
            rec["fecha_hora"] = fecha_hora
            rec["turno"] = turno

            # Diversificar perfiles del día para tener VERDE/AMARILLO/ROJO en ICS
            # green ~ valores 1-2 predominan; yellow ~ muchos 3, pocos 4; red ~ más 4-5
            day_profile = random.choices(["green", "yellow", "red"], weights=[0.45, 0.4, 0.15])[0]

            def clamp(v: int) -> int:
                return max(1, min(5, v))

            def sample_metric(profile: str) -> int:
                if profile == "green":
                    return random.choices([1, 2, 3], weights=[55, 35, 10])[0]
                if profile == "yellow":
                    return random.choices([1, 2, 3, 4], weights=[10, 25, 45, 20])[0]
                # red
                return random.choices([2, 3, 4, 5], weights=[10, 30, 40, 20])[0]

            # Recuperación alta en green; fatiga inversa a recuperación
            rec["recuperacion"] = clamp(sample_metric(day_profile))
            rec["fatiga"] = clamp(6 - rec["recuperacion"] + random.choice([-1, 0, 0, 1]))
            # Sueño y estrés según perfil
            rec["sueno"] = clamp(sample_metric(day_profile))
            rec["stress"] = clamp(sample_metric(day_profile))

            # Dolor: mantener bajo en green/yellow para evitar que ICS se vuelva ROJO por una sola variable
            if day_profile == "green":
                rec["dolor"] = random.choices([1, 2], weights=[80, 20])[0]
            elif day_profile == "yellow":
                rec["dolor"] = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
            else:
                rec["dolor"] = random.choices([2, 3, 4, 5], weights=[20, 35, 30, 15])[0]

            # Partes con dolor solo si dolor > 1
            if rec["dolor"] > 1 and partes_opts:
                k = random.randint(1, min(2, len(partes_opts)))
                rec["partes_cuerpo_dolor"] = random.sample(partes_opts, k)
            else:
                rec["partes_cuerpo_dolor"] = []

            # Extras
            rec["periodizacion_tactica"] = random.randint(-3, 3)
            rec["en_periodo"] = random.random() < 0.15
            rec["observacion"] = ""

            # Upsert (merge con existente si lo hay)
            upsert_jsonl(rec)
            total_created += 1

    return {
        "backup": backup_path,
        "created": total_created,
        "skipped": skipped_existing,
        "target": REGISTROS_JSONL,
        "days": days,
    }
