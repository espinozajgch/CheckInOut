import pandas as pd
from src.db_connection import get_connection
import streamlit as st
import json
from src.schema import MAP_POSICIONES

import json
import streamlit as st

@st.cache_data(ttl=3600)  # Cachea por 1 hora
def get_records_wellness_db(as_df: bool = True):
    """
    Carga todos los registros de la tabla 'registros_wellness' desde la base de datos MySQL.
    - as_df=True  → devuelve un DataFrame (por defecto)
    - as_df=False → devuelve lista de diccionarios
    
    Añade columnas auxiliares:
    - fecha (datetime)
    - fecha_dia (date)
    - partes_cuerpo_dolor (como lista Python si está en JSON)
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo establecer conexión con la base de datos.")
        return pd.DataFrame() if as_df else []

    try:
        query = """
            SELECT * FROM registros_wellness ORDER BY fecha_hora DESC;
        """

        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return pd.DataFrame() if as_df else []

        df = pd.DataFrame(rows)

        # --- Procesar fechas ---
        df["fecha"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
        df["fecha_dia"] = df["fecha"].dt.date

        # --- Procesar JSON de partes_cuerpo_dolor ---
        if "partes_cuerpo_dolor" in df.columns:
            df["partes_cuerpo_dolor"] = df["partes_cuerpo_dolor"].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.strip().startswith("[") else []
            )

        # --- Reemplazar NaN con valores por defecto ---
        # df = df.fillna({
        #     "turno": "",
        #     "observacion": "",
        #     "partes_cuerpo_dolor": [],
        # })

        if as_df:
            return df
        else:
            return df.to_dict(orient="records")

    except Exception as e:
        st.error(f":material/warning: Error al cargar registros de wellness: {e}")
        return pd.DataFrame() if as_df else []
    finally:
        conn.close()

import json
import datetime
import streamlit as st
from src.db_connection import get_connection


def upsert_wellness_record(record: dict) -> bool:
    """
    Inserta o actualiza un registro de wellness en la base de datos MySQL.
    Criterio de unicidad: (identificacion, fecha_dia, turno)
    
    Si ya existe un registro con la misma jugadora, fecha y turno → se actualiza.
    Si no existe → se inserta.
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo establecer conexión con la base de datos.")
        return False

    try:
        cursor = conn.cursor()

        # --- Preparar datos base ---
        fecha_hora = record.get("fecha_hora")
        if isinstance(fecha_hora, str):
            fecha_hora = datetime.datetime.fromisoformat(fecha_hora)
        fecha_dia = fecha_hora.date()

        partes_json = json.dumps(record.get("partes_cuerpo_dolor", []))

        # --- 1️⃣ Verificar si ya existe ---
        check_query = """
            SELECT id FROM registros_wellness
            WHERE identificacion = %s
              AND DATE(fecha_hora) = %s
              AND turno = %s
            LIMIT 1;
        """
        cursor.execute(check_query, (
            record.get("identificacion"),
            fecha_dia,
            record.get("turno"),
        ))
        existing = cursor.fetchone()

        # --- 2️⃣ Si existe → UPDATE ---
        if existing:
            update_query = """
                UPDATE registros_wellness
                SET 
                    nombre = %s,
                    fecha_hora = %s,
                    tipo = %s,
                    periodizacion_tactica = %s,
                    recuperacion = %s,
                    fatiga = %s,
                    sueno = %s,
                    stress = %s,
                    dolor = %s,
                    partes_cuerpo_dolor = %s,
                    minutos_sesion = %s,
                    rpe = %s,
                    ua = %s,
                    en_periodo = %s,
                    observacion = %s
                WHERE id = %s;
            """
            cursor.execute(update_query, (
                record.get("nombre"),
                fecha_hora,
                record.get("tipo"),
                record.get("periodizacion_tactica"),
                record.get("recuperacion"),
                record.get("fatiga"),
                record.get("sueno"),
                record.get("stress"),
                record.get("dolor"),
                partes_json,
                record.get("minutos_sesion"),
                record.get("rpe"),
                record.get("ua"),
                record.get("en_periodo"),
                record.get("observacion"),
                existing[0],
            ))

        # --- 3️⃣ Si no existe → INSERT ---
        else:
            insert_query = """
                INSERT INTO registros_wellness (
                    identificacion, nombre, fecha_hora, tipo, turno,
                    periodizacion_tactica, recuperacion, fatiga, sueno,
                    stress, dolor, partes_cuerpo_dolor,
                    minutos_sesion, rpe, ua, en_periodo, observacion
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s
                );
            """
            cursor.execute(insert_query, (
                record.get("identificacion"),
                record.get("nombre"),
                fecha_hora,
                record.get("tipo"),
                record.get("turno"),
                record.get("periodizacion_tactica"),
                record.get("recuperacion"),
                record.get("fatiga"),
                record.get("sueno"),
                record.get("stress"),
                record.get("dolor"),
                partes_json,
                record.get("minutos_sesion"),
                record.get("rpe"),
                record.get("ua"),
                record.get("en_periodo"),
                record.get("observacion"),
            ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        st.error(f":material/warning: Error al insertar/actualizar registro de wellness: {e}")
        return False

    finally:
        cursor.close()
        conn.close()

def get_ultima_lesion_id_por_jugadora(id_jugadora: str) -> str | None:
    """
    Devuelve el ID de la última lesión registrada de una jugadora.
    Si no tiene lesiones, retorna None.
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo conectar a la base de datos.")
        return None

    try:
        query = """
        SELECT id_lesion
        FROM lesiones
        WHERE id_jugadora = %s
        ORDER BY COALESCE(fecha_hora_registro, fecha_lesion) DESC
        LIMIT 1;
        """

        cursor = conn.cursor()
        cursor.execute(query, (id_jugadora,))
        result = cursor.fetchone()

        return result[0] if result else None

    except Exception as e:
        st.error(f":material/warning: Error al obtener el ID de la última lesión: {e}")
        return None

    finally:
        if conn:
            conn.close()

def get_records_plus_players_db(plantel: str = None) -> pd.DataFrame:
    """
    Devuelve todas las lesiones junto con los datos de las jugadoras.
    Si no hay registros, devuelve un DataFrame vacío.

    Combina:
    - lesiones
    - futbolistas (nombre, apellido, competicion)
    - informacion_futbolistas (posicion, altura, peso)
    """

    conn = get_connection()
    if not conn:
        st.error(":material/warning: No se pudo conectar a la base de datos.")
        return pd.DataFrame()

    try:
        query = """
        SELECT 
            l.id AS id_registro,
            l.id_lesion,
            l.id_jugadora,
            f.nombre,
            f.apellido,
            f.competicion AS plantel,
            i.posicion,
            l.fecha_lesion,
            l.estado_lesion,
            l.diagnostico,
            l.dias_baja_estimado,
            l.impacto_dias_baja_estimado,
            l.mecanismo_id,
            m.nombre AS mecanismo,
            t.nombre AS tipo_lesion,
            te.nombre AS tipo_especifico,
            l.lugar_id,
            lu.nombre AS lugar,
            l.segmento_id,
            s.nombre AS segmento,
            l.zona_cuerpo_id,
            z.nombre AS zona_cuerpo,
            l.zona_especifica_id,
            za.nombre AS zona_especifica,
            l.lateralidad,
            l.es_recidiva,
            l.tipo_recidiva,
            l.tipo_tratamiento,
            l.personal_reporta,
            l.fecha_alta_diagnostico,
            l.fecha_alta_medica,
            l.fecha_alta_deportiva,
            l.descripcion,
            l.evolucion,
            l.fecha_hora_registro,
            l.usuario
        FROM lesiones l
        LEFT JOIN futbolistas f ON l.id_jugadora = f.id
        LEFT JOIN informacion_futbolistas i ON l.id_jugadora = i.id_futbolista
        LEFT JOIN lugares lu ON l.lugar_id = lu.id
        LEFT JOIN mecanismos m ON l.mecanismo_id = m.id
        LEFT JOIN tipo_lesion t ON l.tipo_lesion_id = t.id
        LEFT JOIN tipo_especifico_lesion te ON l.tipo_especifico_id = te.id
        LEFT JOIN segmentos_corporales s ON l.segmento_id = s.id
        LEFT JOIN zonas_segmento z ON l.zona_cuerpo_id = z.id
        LEFT JOIN zonas_anatomicas za ON l.zona_especifica_id = za.id
        ORDER BY l.fecha_hora_registro DESC;
        """

        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        cursor.close()

        if not rows:
            st.info(":material/info: No existen registros de lesiones en la base de datos.")
            st.stop()

        # Crear columna nombre_jugadora
        df["nombre_jugadora"] = (
            df["nombre"].fillna("") + " " + df["apellido"].fillna("")
        ).str.strip()

        # Reordenar columnas
        columnas = df.columns.tolist()
        if "id_jugadora" in columnas and "nombre_jugadora" in columnas:
            idx = columnas.index("id_jugadora") + 1
            columnas.insert(idx, columnas.pop(columnas.index("nombre_jugadora")))
        if "posicion" in columnas and "plantel" in columnas:
            idx = columnas.index("posicion") + 1
            columnas.insert(idx, columnas.pop(columnas.index("plantel")))

        df = df[columnas]
        df["posicion"] = df["posicion"].map(MAP_POSICIONES).fillna(df["posicion"])
        df["sesiones"] = df["evolucion"].apply(contar_sesiones)
        
        # Filtrar por plantel si se indica
        if plantel:
            df = df[df["plantel"] == plantel]

        if st.session_state["auth"]["rol"].lower() == "developer":
            df = df[df["usuario"]=="developer"]
        else:
            df = df[df["usuario"]!="developer"]
        
        return df

    except Exception as e:
        st.error(f":material/warning: Error al cargar registros y jugadoras: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

@st.cache_data(ttl=3600)  # cachea por 1 hora (ajústalo según tu frecuencia de actualización)
def load_jugadoras_db() -> tuple[pd.DataFrame | None, str | None]:
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
            f.id AS identificacion,
            f.nombre,
            f.apellido,
            f.competicion AS plantel,
            f.fecha_nacimiento,
            f.sexo,
            i.posicion,
            i.dorsal,
            i.nacionalidad,
            i.altura,
            i.peso,
            i.foto_url
        FROM futbolistas f
        LEFT JOIN informacion_futbolistas i 
            ON f.id = i.id_futbolista
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
            "identificacion", "nombre_jugadora", "nombre", "apellido", "posicion", "plantel",
            "dorsal", "nacionalidad", "altura", "peso", "fecha_nacimiento",
            "sexo", "foto_url"
        ]
        df = df[[col for col in orden if col in df.columns]]
        df["posicion"] = df["posicion"].map(MAP_POSICIONES).fillna(df["posicion"])

        #st.dataframe(df)

        return df, None

    except Exception as e:
        return None, f":material/warning: Error al cargar jugadoras: {e}"

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
            return None, ":material/warning: No se encontraron registros en la tabla 'plantel'."

        # Limpieza básica
        df["nombre"] = df["nombre"].astype(str).str.strip().str.title()
        df["codigo"] = df["codigo"].astype(str).str.strip().str.upper()

        # Reordenar columnas (por consistencia)
        orden = ["id", "nombre", "codigo"]
        df = df[[col for col in orden if col in df.columns]]

        return df, None

    except Exception as e:
        return None, f":material/warning: Error al cargar competiciones: {e}"

    finally:
        conn.close()