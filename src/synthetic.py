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
from .ui_components import validate_checkout
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


def generate_synthetic_full(days: int = 30, seed: int = 777) -> dict:
    """Genera datos completos (Check-in y Check-out) para TODAS las jugadoras
    para los últimos N días, asignando una periodización táctica que avanza
    cronológicamente día a día. Se usa un único turno por jugadora y día.

    - Check-in: 08:00–11:00 aprox, wellness 1..5 + periodización_tactica progresiva
    - Check-out: 17:00–21:00 aprox, minutos, RPE y UA = minutos * RPE
    - Upsert por (jugadora, día, turno) para fusionar ambos registros
    """

    random.seed(seed)

    # 🔹 Cargar jugadoras desde JSON usando tu método original
    players = _load_players_safe()

    # 🔹 Calcular rango de fechas
    end_day = datetime.now().date() - timedelta(days=1)
    end_dt = datetime.combine(end_day, time(12, 0, 0))

    backup_path = _backup_registros()

    turnos = ["Turno 1", "Turno 2", "Turno 3"]
    total_upserts = 0

    # 🔹 Secuencia cíclica de periodización táctica (-6..+6)
    def pt_sequence(n: int):
        vals = []
        cur = -6
        for _ in range(n):
            vals.append(cur)
            cur += 1
            if cur > 6:
                cur = -6
        return vals

    days_list = [end_dt - timedelta(days=i) for i in range(days)][::-1]
    day_pts = pt_sequence(len(days_list))

    created_ci = 0
    created_co = 0

    for idx, d in enumerate(days_list):
        pt_val = day_pts[idx]
        for _, row in players.iterrows():
            jug_id = str(row["identificacion"])
            jug_name = str(row["nombre"])
            turno = random.choice(turnos)

            # --- Check-in ---
            h_in = random.randint(7, 11)
            m_in = random.randint(0, 59)
            s_in = random.randint(0, 59)
            fecha_ci = datetime.combine(d.date(), time(h_in, m_in, s_in)).strftime("%Y-%m-%dT%H:%M:%S")

            rec_in = new_base_record(id_jugadora=jug_id, nombre_jugadora=jug_name, tipo="checkIn")
            rec_in["fecha_hora"] = fecha_ci
            rec_in["turno"] = turno
            rec_in["periodizacion_tactica"] = pt_val

            # --- Variables Wellness ---
            def clamp(v: int, lo: int = 1, hi: int = 5) -> int:
                return max(lo, min(hi, v))

            base = random.choice([2, 3])
            rec_in["recuperacion"] = clamp(base + random.choice([-1, 0, 0, 1]))
            rec_in["fatiga"] = clamp(6 - rec_in["recuperacion"] + random.choice([-1, 0, 0, 1]))
            rec_in["sueno"] = clamp(base + random.choice([-1, 0, 1]))
            rec_in["stress"] = clamp(base + random.choice([-1, 0, 1]))
            rec_in["dolor"] = clamp(random.choices([1, 2, 3, 4], weights=[60, 25, 12, 3])[0])

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