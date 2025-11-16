import streamlit as st
import pandas as pd
import json
import datetime

from src.schema import MAP_POSICIONES
from src.db.db_connection import get_connection

def get_records_db(as_df: bool = True):
    """
    Carga todos los registros de la tabla 'wellness' desde la base de datos MySQL,
    uniendo los nombres descriptivos de los catálogos de estímulos.

    - as_df=True  → devuelve un DataFrame (por defecto)
    - as_df=False → devuelve lista de diccionarios

    Joins:
    - wellness.id_tipo_estimulo → estimulos_campo.id
    - wellness.id_tipo_readaptacion → estimulos_readaptacion.id

    Añade columnas procesadas:
    - partes_cuerpo_dolor (list Python)
    - fecha_sesion (datetime)
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo establecer conexión con la base de datos.")
        return pd.DataFrame() if as_df else []

    try:
        query = """
            SELECT 
                w.id,
                w.id_jugadora,
                f.nombre,
                f.apellido,
                f.competicion as plantel,
                w.fecha_sesion,
                w.tipo,
                w.turno,
                w.recuperacion,
                w.fatiga as energia,
                w.sueno,
                w.stress,
                w.dolor,
                w.partes_cuerpo_dolor,
                w.periodizacion_tactica,
                ec.nombre AS tipo_estimulo,
                er.nombre AS tipo_readaptacion,
                w.minutos_sesion,
                w.rpe,
                w.ua,
                w.en_periodo,
                w.observacion,
                w.fecha_hora_registro,
                w.usuario
            FROM wellness AS w
            LEFT JOIN futbolistas f ON w.id_jugadora = f.identificacion
            LEFT JOIN estimulos_campo AS ec 
                ON w.id_tipo_estimulo = ec.id
            LEFT JOIN estimulos_readaptacion AS er 
                ON w.id_tipo_readaptacion = er.id
            WHERE f.genero = 'F' and w.estatus_id <= 2
            ORDER BY w.fecha_hora_registro DESC;
        """

        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return pd.DataFrame() if as_df else []

        # --- Crear DataFrame ---
        df = pd.DataFrame(rows)

        # --- Procesar JSON (partes_cuerpo_dolor) ---
        if "partes_cuerpo_dolor" in df.columns:
            df["partes_cuerpo_dolor"] = df["partes_cuerpo_dolor"].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.strip().startswith("[") else []
            )

        # --- Procesar fechas ---
        if "fecha_sesion" in df.columns:
            df["fecha_sesion"] = (
                pd.to_datetime(df["fecha_sesion"], errors="coerce")
                .apply(lambda x: x.date() if pd.notnull(x) else None)
            )

        if "fecha_hora_registro" in df.columns:
            df["fecha_hora_registro"] = pd.to_datetime(df["fecha_hora_registro"], errors="coerce")

        # --- Ordenar de forma más reciente a más antigua ---
        df = df.sort_values(by="fecha_hora_registro", ascending=False)

        if st.session_state["auth"]["rol"].lower() == "developer":
            df = df[df["usuario"]=="developer"]
        else:
            df = df[df["usuario"]!="developer"]

        # Crear columna nombre_jugadora y colocarla en la segunda posición
        nombre_jugadora = (df["nombre"].fillna("") + " " + df["apellido"].fillna("")).str.strip()
        df.insert(2, "nombre_jugadora", nombre_jugadora)

        df = df.drop(columns=["nombre", "apellido"], errors="ignore")

        # print(df["fecha_sesion"].head())
        # print(df["fecha_sesion"].dtype)
        # print(type(df["fecha_sesion"].iloc[0]))

        # --- Retornar según formato deseado ---
        return df if as_df else df.to_dict(orient="records")

    except Exception as e:
        st.error(f":material/warning: Error al cargar los registros de wellness: {e}")
        return pd.DataFrame() if as_df else []
    finally:
        conn.close()

def get_record_for_player_day_turno_db(id_jugadora: str, fecha_sesion: str, turno: str):
    """
    Devuelve el primer registro existente en la BD 'wellness'
    para una jugadora, una fecha de sesión y un turno dados.

    Parámetros:
        id_jugadora (str): ID o documento de la jugadora.
        fecha_sesion (str): Fecha en formato 'YYYY-MM-DD'.
        turno (str): Turno del entrenamiento.

    Retorna:
        dict | None: Registro encontrado o None si no existe.
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo establecer conexión con la base de datos.")
        return None

    try:
        cursor = conn.cursor(dictionary=True)

        # --- Normalizar fecha y turno ---
        turno = (turno or "").strip()
        if isinstance(fecha_sesion, str):
            try:
                fecha_sesion = datetime.date.fromisoformat(fecha_sesion)
            except ValueError:
                st.error(f":material/warning: Formato de fecha inválido: {fecha_sesion}")
                return None

        # --- Logging modo developer ---
        rol_actual = st.session_state["auth"]["rol"].lower().strip()

        if rol_actual == "developer":
            # --- Buscar el registro en la BD ---
            query = """
                SELECT *
                FROM wellness
                WHERE id_jugadora = %s
                AND fecha_sesion = %s
                AND turno = %s
                AND usuario = %s
                AND estatus_id <= 2
                LIMIT 1;
            """
            usuario = rol_actual
        else:
            query = """
                SELECT *
                FROM wellness
                WHERE id_jugadora = %s
                AND fecha_sesion = %s
                AND turno = %s
                AND usuario != %s
                AND estatus_id <= 2
                LIMIT 1;
            """

            usuario = "developer"

        cursor.execute(query, (id_jugadora, fecha_sesion, turno, usuario))
        record = cursor.fetchone()

        # if rol_actual == "developer":
        #     st.write(f"🟡 Query ejecutada):")
        #     st.code(query, language="sql")
        #     st.json((id_jugadora, fecha_sesion, turno))

        # --- Convertir JSON a lista Python ---
        if record and record.get("partes_cuerpo_dolor"):
            try:
                record["partes_cuerpo_dolor"] = json.loads(record["partes_cuerpo_dolor"])
            except Exception:
                record["partes_cuerpo_dolor"] = []

        return record

    except Exception as e:
        st.error(f":material/warning: Error al obtener registro de wellness por dia y turno: {e}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
          
def upsert_wellness_record_db(record: dict, modo: str = "checkin") -> bool:
    """
    Inserta o actualiza un registro de wellness en la base de datos MySQL.
    Criterio de unicidad: (id_jugadora, fecha_sesion, turno)

    - Si modo == "checkin": inserta o actualiza todos los campos del registro.
    - Si modo == "checkout": solo actualiza los campos del post-entrenamiento
      (minutos_sesion, rpe, ua y tipo).
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo establecer conexión con la base de datos.")
        return False

    try:
        usuario_actual = st.session_state["auth"]["username"]
        cursor = conn.cursor(dictionary=True)

        # ============================================================
        # 🔹 Normalización de datos
        # ============================================================
        fecha_sesion = record.get("fecha_sesion")
        if isinstance(fecha_sesion, str):
            fecha_sesion = datetime.date.fromisoformat(fecha_sesion)

        partes_json = json.dumps(record.get("partes_cuerpo_dolor", []), ensure_ascii=False)

        # ============================================================
        # 🔹 Verificar si ya existe el registro
        # ============================================================
        check_query = """
            SELECT id FROM wellness
            WHERE id_jugadora = %s
              AND fecha_sesion = %s
              AND turno = %s
              AND estatus_id <= 2
            LIMIT 1;
        """
        cursor.execute(
            check_query,
            (
                record.get("id_jugadora"),
                fecha_sesion,
                record.get("turno"),
            ),
        )
        existing = cursor.fetchone()

        # ============================================================
        # 🟡 Si existe → UPDATE
        # ============================================================
        if existing:
            if modo.lower() == "checkout":
                # --- Solo actualizar los campos de carga post-sesión ---
                update_query = """
                    UPDATE wellness
                    SET 
                        tipo = 'checkOut',
                        minutos_sesion = %(minutos_sesion)s,
                        rpe = %(rpe)s,
                        ua = %(ua)s,
                        modified_by = %(modified_by)s,
                        estatus_id = 2,
                        updated_at = NOW()
                    WHERE id = %(id)s;
                """
                params = {
                    "minutos_sesion": record.get("minutos_sesion"),
                    "rpe": record.get("rpe"),
                    "ua": record.get("ua"),
                    "modified_by": usuario_actual,
                    "id": existing["id"],
                }

            else:
                # --- Actualización completa (check-in o edición general) ---
                update_query = """
                    UPDATE wellness
                    SET 
                        tipo = %(tipo)s,
                        periodizacion_tactica = %(periodizacion_tactica)s,
                        id_tipo_estimulo = %(id_tipo_estimulo)s,
                        id_tipo_readaptacion = %(id_tipo_readaptacion)s,
                        recuperacion = %(recuperacion)s,
                        fatiga = %(fatiga)s,
                        sueno = %(sueno)s,
                        stress = %(stress)s,
                        dolor = %(dolor)s,
                        partes_cuerpo_dolor = %(partes_cuerpo_dolor)s,
                        minutos_sesion = %(minutos_sesion)s,
                        rpe = %(rpe)s,
                        ua = %(ua)s,
                        en_periodo = %(en_periodo)s,
                        observacion = %(observacion)s,
                        usuario = %(usuario)s,
                        fecha_hora_registro = CURRENT_TIMESTAMP
                    WHERE id = %(id)s;
                """
                params = dict(record)
                params["partes_cuerpo_dolor"] = partes_json
                params["id"] = existing["id"]

            # --- Logging modo developer ---
            if st.session_state["auth"]["rol"].lower() == "developer":
                st.write(f"🟡 Query UPDATE ejecutada (modo={modo.upper()}):")
                st.code(update_query, language="sql")
                st.json(params)

            cursor.execute(update_query, params)
            conn.commit()
            return True

        # ============================================================
        # 🟢 Si no existe → INSERT (solo modo checkin)
        # ============================================================
        else:
            if modo.lower() == "checkout":
                st.warning(":material/warning: No existe un check-in previo para este jugador, fecha y turno.")
                return False

            insert_query = """
                INSERT INTO wellness (
                    id_jugadora, fecha_sesion, tipo, turno, periodizacion_tactica,
                    id_tipo_estimulo, id_tipo_readaptacion, recuperacion, fatiga, sueno,
                    stress, dolor, partes_cuerpo_dolor, minutos_sesion, rpe, ua,
                    en_periodo, observacion, usuario
                ) VALUES (
                    %(id_jugadora)s, %(fecha_sesion)s, %(tipo)s, %(turno)s, %(periodizacion_tactica)s,
                    %(id_tipo_estimulo)s, %(id_tipo_readaptacion)s, %(recuperacion)s, %(fatiga)s, %(sueno)s,
                    %(stress)s, %(dolor)s, %(partes_cuerpo_dolor)s, %(minutos_sesion)s, %(rpe)s, %(ua)s,
                    %(en_periodo)s, %(observacion)s, %(usuario)s
                );
            """

            params = dict(record)
            params["fecha_sesion"] = fecha_sesion
            params["partes_cuerpo_dolor"] = partes_json

            if st.session_state["auth"]["rol"].lower() == "developer":
                st.write("🟢 Query INSERT ejecutada:")
                st.code(insert_query, language="sql")
                st.json(params)

            cursor.execute(insert_query, params)
            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        st.error(f":material/warning: Error al insertar/actualizar registro de wellness: {e}")

        if st.session_state.get("auth", {}).get("rol").lower() == "developer":
            st.json(record)

        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@st.cache_data(ttl=3600)  # cachea por 1 hora (ajústalo según tu frecuencia de actualización)
def load_jugadoras_db() -> pd.DataFrame | None:
    """
    Carga jugadoras desde la base de datos (futbolistas + informacion_futbolistas).
    
    Devuelve:
        tuple: (DataFrame o None, mensaje de error o None)
    """
    conn = get_connection()
    if not conn:
        return None, ":material/warning: No se pudo conectar a la base de datos."

    try:
        query = """
        SELECT 
            f.id,
            f.identificacion AS id_jugadora,
            f.nombre,
            f.apellido,
            f.competicion AS plantel,
            f.fecha_nacimiento,
            f.genero,
            i.posicion,
            i.dorsal,
            i.nacionalidad,
            i.altura,
            i.peso,
            i.foto_url,
            i.foto_url_drive
        FROM futbolistas f
        LEFT JOIN informacion_futbolistas i 
            ON f.identificacion = i.identificacion
        WHERE f.genero = 'F'
        ORDER BY f.nombre ASC;
        """

        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        cursor.close()

        # Limpiar y preparar los datos
        df["nombre"] = df["nombre"].astype(str).str.strip().str.title()
        df["apellido"] = df["apellido"].astype(str).str.strip().str.title()

        # Crear columna nombre completo
        df["nombre_jugadora"] = (df["nombre"] + " " + df["apellido"]).str.strip()

        # Reordenar columnas
        orden = [
            "id", "id_jugadora", "nombre_jugadora", "nombre", "apellido", "posicion", "plantel",
            "dorsal", "nacionalidad", "altura", "peso", "fecha_nacimiento",
            "genero", "foto_url"
        ]
        df = df[[col for col in orden if col in df.columns]]
        df["posicion"] = df["posicion"].map(MAP_POSICIONES).fillna(df["posicion"])

        df = df.drop(columns=["nombre", "apellido"], errors="ignore")

        return df

    except Exception as e:
            st.error(f":material/warning: Error al cargar jugadoras: {e}")
            st.stop()
    finally:
        conn.close()

@st.cache_data(ttl=3600)  # cachea por 1 hora
def load_competiciones_db() -> tuple[pd.DataFrame | None, str | None]:
    """
    Carga competiciones desde la base de datos (tabla 'plantel').

    Devuelve:
        tuple: (DataFrame o None, mensaje de error o None)
    """
    conn = get_connection()
    if not conn:
        return None, ":material/warning: No se pudo conectar a la base de datos."

    try:
        query = """
        SELECT 
            id,
            nombre,
            codigo
        FROM plantel
        ORDER BY nombre ASC;
        """

        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        cursor.close()

        if df.empty:
            st.error(":material/warning: No se encontraron registros en la tabla 'plantel'.")
            st.stop()

        # Limpieza básica
        df["nombre"] = df["nombre"].astype(str).str.strip().str.title()
        df["codigo"] = df["codigo"].astype(str).str.strip().str.upper()

        # Reordenar columnas (por consistencia)
        orden = ["id", "nombre", "codigo"]
        df = df[[col for col in orden if col in df.columns]]

        return df

    except Exception as e:
        st.error(f":material/warning: Error al cargar competiciones: {e}")
        st.stop()
    finally:
        conn.close()

# def delete_wellness(ids: list[int]) -> tuple[bool, str]:
#     """
#     Elimina múltiples wellness desde la base de datos.

#     Parámetros:
#         ids (list[int]): lista de IDs de wellness a eliminar.

#     Retorna:
#         (bool, str): (éxito, mensaje)
#     """
#     if not ids:
#         return False, "No se proporcionaron IDs de wellness."

#     try:
#         conn = get_connection()
#         cursor = conn.cursor(dictionary=True)

#         # Construir la query dinámica con placeholders
#         query = f"DELETE FROM wellness WHERE id IN ({','.join(['%s'] * len(ids))})"
#         cursor.execute(query, tuple(ids))
#         conn.commit()

#         cursor.close()
#         conn.close()

#         return True, f"✅ Se eliminaron {cursor.rowcount} registro(s) correctamente."

#     except Exception as e:
#         st.error(f":material/warning: Error al eliminar los registros: {e}")
#         return False, f":material/warning: Error al eliminar los registros: {e}"

def delete_wellness(ids: list[int]) -> tuple[bool, str]:
    """
    Soft-delete: marca registros de wellness como eliminados (estatus_id = 3).
    
    Parámetros:
        ids (list[int]): lista de IDs de wellness a eliminar.

    Retorna:
        (bool, str): (éxito, mensaje)
    """
    if not ids:
        return False, "No se proporcionaron IDs de wellness."

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Datos de auditoría
        deleted_by = st.session_state["auth"]["username"]
        
        # Construir query dinámica con placeholders
        placeholders = ",".join(["%s"] * len(ids))
        
        query = f"""
            UPDATE wellness
            SET 
                estatus_id = 3,
                deleted_at = NOW(),
                deleted_by = %s
            WHERE id IN ({placeholders})
        """

        # Ejecutar query (primero deleted_by, luego ids)
        cursor.execute(query, tuple([deleted_by] + ids))
        conn.commit()

        afectados = cursor.rowcount

        cursor.close()
        conn.close()

        return True, f"Se eliminaron {afectados} registro(s) correctamente."

    except Exception as e:
        st.error(f":material/warning: Error al eliminar los registros: {e}")
        return False, f":material/warning: Error al eliminar los registros: {e}"
