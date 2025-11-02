import random
from datetime import datetime, timedelta, time
import os
import shutil
import pandas as pd

from .io_files import (
    upsert_jsonl,
    load_jugadoras,
    DATA_DIR,
    REGISTROS_JSONL
)
from .schema import new_base_record

def _backup_registros() -> str | None:
    if os.path.exists(REGISTROS_JSONL):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"registros.backup_{ts}.jsonl")
        shutil.copy(REGISTROS_JSONL, backup_path)
        return backup_path
    return None

def _load_players_safe():
    """
    Wrapper que garantiza que load_jugadoras() devuelva un DataFrame válido.
    Lanza un ValueError si ocurre un error en la carga.
    """
    df, error = load_jugadoras()
    if error:
        raise ValueError(f"Error cargando jugadoras: {error}")
    return df

def generate_synthetic_full(days: int = 30, seed: int = 777, partidos_semana: int = 1) -> dict:
    """
    Genera datos completos (Check-in y Check-out) para todas las jugadoras,
    con periodización táctica realista entre MD–6 y MD+1.
    
    - Soporta escenarios de 1 o 2 partidos por semana.
    - Ajusta la carga (minutos, RPE, wellness) según el tipo de día en el microciclo.
    """

    random.seed(seed)

    players = _load_players_safe()
    end_day = datetime.now().date() - timedelta(days=1)
    end_dt = datetime.combine(end_day, time(12, 0, 0))
    backup_path = _backup_registros()

    turnos = ["Turno 1", "Turno 2", "Turno 3"]
    created_ci = created_co = 0

    # --- Secuencia cíclica corregida: MD–6 → MD+1 ---
    def pt_sequence(n: int, partidos: int):
        seq = []
        if partidos == 1:
            base = list(range(-6, 2))  # -6,-5,-4,-3,-2,-1,0,1
        else:
            base = list(range(-3, 2))  # -3,-2,-1,0,1
        for i in range(n):
            seq.append(base[i % len(base)])  # reinicia automáticamente
        return seq

    days_list = [end_dt - timedelta(days=i) for i in range(days)][::-1]
    day_pts = pt_sequence(len(days_list), partidos_semana)

    # --- Perfil fisiológico teórico por fase ---
    phase_profiles = {
        -6: {"rpe": (3, 0.5), "min": (50, 10), "well": (4, 5)},  # Regenerativo
        -5: {"rpe": (4, 0.7), "min": (65, 10), "well": (3, 5)},
        -4: {"rpe": (5, 0.8), "min": (75, 10), "well": (3, 4)},
        -3: {"rpe": (7, 0.8), "min": (85, 10), "well": (2, 4)},  # Carga alta
        -2: {"rpe": (6, 0.8), "min": (75, 10), "well": (3, 4)},  # Media táctica
        -1: {"rpe": (5, 0.8), "min": (60, 10), "well": (4, 5)},  # Activación
         0: {"rpe": (9, 0.7), "min": (95, 15), "well": (4, 5)},  # Partido
         1: {"rpe": (3, 0.5), "min": (45, 10), "well": (3, 5)},  # Recuperación
    }

    for idx, d in enumerate(days_list):
        pt_val = day_pts[idx]
        profile = phase_profiles.get(pt_val, {"rpe": (5, 1), "min": (70, 10), "well": (3, 4)})

        for _, row in players.iterrows():
            jug_id = str(row["identificacion"])
            jug_name = str(row["nombre"])
            turno = random.choice(turnos)

            # --- Check-in ---
            h_in = random.randint(7, 11)
            fecha_ci = datetime.combine(d.date(), time(h_in, random.randint(0, 59), random.randint(0, 59)))

            rec_in = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkIn")
            rec_in["fecha_hora"] = fecha_ci.isoformat()
            rec_in["turno"] = turno
            rec_in["periodizacion_tactica"] = pt_val

            def rnd(a, b): return random.randint(a, b)
            rec_in["recuperacion"] = rnd(profile["well"][0], profile["well"][1])
            rec_in["fatiga"] = rnd(1, 6 - rec_in["recuperacion"])
            rec_in["sueno"] = rnd(profile["well"][0], profile["well"][1])
            rec_in["stress"] = rnd(2, 5 if pt_val < 0 else 4)
            rec_in["dolor"] = random.choices([1, 2, 3, 4], weights=[70, 20, 8, 2])[0]
            rec_in["partes_cuerpo_dolor"] = []
            rec_in["en_periodo"] = (random.random() < 0.15)
            rec_in["observacion"] = ""
            upsert_jsonl(rec_in)
            created_ci += 1

            # --- Check-out ---
            h_out = random.randint(17, 21)
            fecha_co = datetime.combine(d.date(), time(h_out, random.randint(0, 59), random.randint(0, 59)))

            rec_out = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkOut")
            rec_out["fecha_hora"] = fecha_co.isoformat()
            rec_out["turno"] = turno
            rec_out["periodizacion_tactica"] = pt_val

            rpe = max(1, min(10, int(round(random.gauss(*profile["rpe"])))))
            minutos = max(40, min(120, int(random.gauss(*profile["min"]))))
            rec_out["rpe"] = rpe
            rec_out["minutos_sesion"] = minutos
            rec_out["ua"] = int(minutos * rpe)
            upsert_jsonl(rec_out)
            created_co += 1

    return {
        "backup": backup_path,
        "created_checkin": created_ci,
        "created_checkout": created_co,
        "total_upserts": created_ci + created_co,
        "target": REGISTROS_JSONL,
        "days": days,
        "partidos_semana": partidos_semana
    }
