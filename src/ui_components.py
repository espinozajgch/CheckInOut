from typing import Dict, Tuple
from datetime import date

import pandas as pd
import streamlit as st

from .io_files import get_template_bytes, load_jugadoras
from .schema import validate_checkin, validate_checkout
from .metrics import compute_rpe_metrics, RPEFilters

def selection_header(jug_df: pd.DataFrame):
    st.subheader("Selección inicial")
    col1, col2, col3 = st.columns(3)
    with col1:
        jugadora_opt = None
        if jug_df is not None and len(jug_df) > 0:
            names = jug_df["nombre_jugadora"].astype(str).tolist()
            selected_name = st.selectbox("Jugadora", options=["- Selecciona -"] + names, index=0)
            if selected_name != "- Selecciona -":
                row = jug_df[jug_df["nombre_jugadora"].astype(str) == selected_name].iloc[0]
                jugadora_opt = {
                    "id_jugadora": row["id_jugadora"],
                    "nombre_jugadora": row["nombre_jugadora"],
                }
        else:
            st.warning("No hay jugadoras cargadas.")
    with col2:
        tipo = st.radio("Tipo de registro", options=["Check-in", "Check-out"], horizontal=True)
    with col3:
        turno = st.selectbox(
            "Turno",
            options=["Turno 1", "Turno 2", "Turno 3"],
            index=0,
            help="Selecciona el turno de la sesión",
        )
    return jugadora_opt, tipo, turno


def checkin_form(record: Dict, partes_df: pd.DataFrame) -> Tuple[Dict, bool, str]:
    st.subheader("Check-in (preentrenamiento)")

    with st.container():
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            record["recuperacion"] = st.number_input("Recuperación (1-5)", min_value=1, max_value=5, step=1)
        with c2:
            record["fatiga"] = st.number_input("Fatiga (1-5)", min_value=1, max_value=5, step=1)
        with c3:
            record["sueno"] = st.number_input("Sueño (1-5)", min_value=1, max_value=5, step=1)
        with c4:
            record["stress"] = st.number_input("Estrés (1-5)", min_value=1, max_value=5, step=1, key="stress_input")
        with c5:
            record["dolor"] = st.number_input("Dolor (1-5)", min_value=1, max_value=5, step=1)

        if int(record.get("dolor", 0)) > 1:
            opciones = partes_df["parte"].astype(str).tolist() if partes_df is not None else []
            record["partes_cuerpo_dolor"] = st.multiselect(
                "Partes del cuerpo con dolor", options=opciones
            )
        else:
            record["partes_cuerpo_dolor"] = []

    st.markdown("---")
    st.caption("Campos opcionales")

    colA, colB = st.columns([2, 1])
    with colA:
        record["periodizacion_tactica"] = st.slider(
            "Periodización táctica (-6 a +6)", min_value=-6, max_value=6, value=0, step=1
        )
        record["observacion"] = st.text_area("Observación", value="")
    with colB:
        record["en_periodo"] = st.checkbox("En periodo")

    is_valid, msg = validate_checkin(record)
    return record, is_valid, msg


def checkout_form(record: Dict) -> Tuple[Dict, bool, str]:
    st.subheader("Check-out (postentrenamiento)")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        record["minutos_sesion"] = st.number_input("Minutos de la sesión", min_value=0, step=1)
    with col2:
        record["rpe"] = st.number_input("RPE (1-10)", min_value=1, max_value=10, step=1)
    with col3:
        # Auto-calc UA
        minutos = int(record.get("minutos_sesion") or 0)
        rpe = int(record.get("rpe") or 0)
        record["ua"] = int(rpe * minutos) if minutos > 0 and rpe > 0 else None
        st.metric("UA (RPE × minutos)", value=record["ua"] if record["ua"] is not None else "-")

    is_valid, msg = validate_checkout(record)
    return record, is_valid, msg


def preview_record(record: Dict) -> None:
    st.subheader("Previsualización")
    # Header with key fields
    jug = record.get("nombre_jugadora", "-")
    fecha = record.get("fecha_hora", "-")
    turno = record.get("turno", "-")
    tipo = record.get("tipo", "-")
    st.markdown(f"**Jugadora:** {jug}  |  **Fecha:** {fecha}  |  **Turno:** {turno}  |  **Tipo:** {tipo}")
    with st.expander("Ver registro JSON", expanded=True):
        import json

        st.code(json.dumps(record, ensure_ascii=False, indent=2), language="json")


def show_missing_file_help(title: str, description: str, template_type: str) -> None:
    st.error(title)
    st.write(description)
    st.info("Puedes descargar una plantilla y subirla a la carpeta data/")

    bytes_xlsx = get_template_bytes(template_type)
    filename = f"{template_type}.template.xlsx"
    st.download_button(
        label=f"Descargar plantilla {template_type}.xlsx",
        data=bytes_xlsx,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def responses_view(df: pd.DataFrame) -> None:
    st.subheader("Respuestas registradas")
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return

    # Filters
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            jugadores = sorted(df["nombre_jugadora"].dropna().astype(str).unique().tolist()) if "nombre_jugadora" in df.columns else []
            jug_sel = st.multiselect("Jugadora(s)", options=jugadores, default=[])
        with col2:
            tipos = ["checkIn", "checkOut"]
            tipo_sel = st.multiselect("Tipo", options=tipos, default=[])
        with col3:
            min_date = df["fecha"].min().date() if "fecha" in df.columns and not df["fecha"].isna().all() else None
            max_date = df["fecha"].max().date() if "fecha" in df.columns and not df["fecha"].isna().all() else None
            if min_date and max_date:
                start, end = st.date_input(
                    "Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date
                )
            else:
                start, end = None, None
        with col4:
            # Fixed turno options; limit to those present in the DF if available
            turno_options = ["Turno 1", "Turno 2", "Turno 3"]
            if "turno" in df.columns:
                present = df["turno"].dropna().astype(str).unique().tolist()
                turno_options = [t for t in turno_options if t in present]
                if not turno_options:
                    turno_options = ["Turno 1", "Turno 2", "Turno 3"]
            turno_sel = st.multiselect("Turno(s)", options=turno_options, default=[])

    filtered = df.copy()
    if jug_sel:
        filtered = filtered[filtered["nombre_jugadora"].astype(str).isin(jug_sel)]
    if tipo_sel:
        filtered = filtered[filtered["tipo"].isin(tipo_sel)]
    if start and end and "fecha" in filtered.columns:
        mask = (filtered["fecha"].dt.date >= start) & (filtered["fecha"].dt.date <= end)
        filtered = filtered[mask]
    if 'turno_sel' in locals() and turno_sel:
        filtered = filtered[filtered["turno"].isin(turno_sel)]

    # Sort by date desc, then turno asc
    sort_cols = [c for c in ["fecha", "turno"] if c in filtered.columns]
    ascending = [False, True][: len(sort_cols)]
    to_show = filtered.sort_values(by=sort_cols, ascending=ascending, na_position="last") if sort_cols else filtered
    st.dataframe(to_show, use_container_width=True)

    # Downloads
    st.markdown("---")
    c1, c2 = st.columns(2)
    # Prepare export-friendly DataFrame: stringify timestamps/dates and replace NaNs
    export_df = filtered.copy()
    if "fecha" in export_df.columns:
        try:
            export_df["fecha"] = export_df["fecha"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            export_df["fecha"] = export_df["fecha"].astype(str)
    if "fecha_dia" in export_df.columns:
        export_df["fecha_dia"] = export_df["fecha_dia"].astype(str)

    with c1:
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar CSV",
            data=csv_bytes,
            file_name="respuestas.csv",
            mime="text/csv",
        )
    with c2:
        import json

        # Replace NaNs/NaTs with None for JSONL
        records = export_df.where(pd.notnull(export_df), None).to_dict(orient="records")
        jsonl_str = "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records)
        st.download_button(
            "Descargar JSONL",
            data=jsonl_str.encode("utf-8"),
            file_name="respuestas.jsonl",
            mime="application/json",
        )


def rpe_view(df: pd.DataFrame) -> None:
    st.subheader("RPE / Cargas")
    if df is None or df.empty:
        st.info("No hay registros aún (se requieren Check-out con UA calculado).")
        return

    # Default date range
    if "fecha" in df.columns and not df["fecha"].isna().all():
        min_date = df["fecha"].min().date()
        max_date = df["fecha"].max().date()
    else:
        min_date = max_date = None

    with st.expander("Filtros", expanded=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            jugadores = (
                sorted(df["nombre_jugadora"].dropna().astype(str).unique().tolist())
                if "nombre_jugadora" in df.columns
                else []
            )
            jug_sel = st.multiselect("Jugadora(s)", options=jugadores, default=[])
        with c2:
            turnos = ["Turno 1", "Turno 2", "Turno 3"]
            if "turno" in df.columns:
                present = df["turno"].dropna().astype(str).unique().tolist()
                turnos = [t for t in turnos if t in present] or ["Turno 1", "Turno 2", "Turno 3"]
            turno_sel = st.multiselect("Turno(s)", options=turnos, default=[])
        with c3:
            if min_date and max_date:
                start, end = st.date_input(
                    "Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date
                )
            else:
                start, end = None, None

    flt = RPEFilters(jugadores=jug_sel or None, turnos=turno_sel or None, start=start, end=end)
    metrics = compute_rpe_metrics(df, flt)

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("UA total día", value=(f"{metrics['ua_total_dia']:.0f}" if metrics["ua_total_dia"] is not None else "-"))
        st.metric("Carga semana", value=(f"{metrics['carga_semana']:.0f}" if metrics["carga_semana"] is not None else "-"))
    with k2:
        st.metric("Carga mes", value=(f"{metrics['carga_mes']:.0f}" if metrics["carga_mes"] is not None else "-"))
        st.metric("Carga media semana", value=(f"{metrics['carga_media_semana']:.1f}" if metrics["carga_media_semana"] is not None else "-"))
    with k3:
        st.metric("Carga media mes", value=(f"{metrics['carga_media_mes']:.1f}" if metrics["carga_media_mes"] is not None else "-"))
        st.metric("Monotonía semana", value=(f"{metrics['monotonia_semana']:.2f}" if metrics["monotonia_semana"] is not None else "-"))
    with k4:
        st.metric("Fatiga aguda (7d)", value=(f"{metrics['fatiga_aguda']:.0f}" if metrics["fatiga_aguda"] is not None else "-"))
        st.metric("Fatiga crónica (28d media)", value=(f"{metrics['fatiga_cronica']:.1f}" if metrics["fatiga_cronica"] is not None else "-"))

    c5, c6, c7 = st.columns(3)
    with c5:
        st.metric("ACWR (aguda:crónica)", value=(f"{metrics['acwr']:.2f}" if metrics["acwr"] is not None else "-"))
    with c6:
        st.metric("Adaptación", value=(f"{metrics['adaptacion']:.2f}" if metrics["adaptacion"] is not None else "-"))
    with c7:
        st.metric("Variabilidad semana (std)", value=(f"{metrics['variabilidad_semana']:.2f}" if metrics["variabilidad_semana"] is not None else "-"))

    st.markdown("---")
    st.caption("Cargas diarias (UA total por día)")
    daily = metrics.get("daily_table")
    if isinstance(daily, pd.DataFrame) and not daily.empty:
        st.dataframe(daily.sort_values("fecha_dia"), use_container_width=True)
        try:
            chart_df = daily.copy()
            chart_df = chart_df.rename(columns={"fecha_dia": "Fecha", "ua_total": "UA"})
            chart_df = chart_df.set_index("Fecha")
            st.line_chart(chart_df["UA"])
        except Exception:
            pass
    else:
        st.info("No hay datos de Check-out con UA en el rango/criterios seleccionados.")


def checkin_view(df: pd.DataFrame) -> None:
    st.subheader("Respuestas Check-in por fecha (plantel)")
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return
    # Mantener registros que contengan respuestas de check-in, aunque el tipo sea 'checkOut' tras el upsert
    d = df.copy()
    checkin_fields = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
    existing_fields = [c for c in checkin_fields if c in d.columns]
    if existing_fields:
        d = d[d[existing_fields].notna().any(axis=1)]
    if d.empty:
        st.info("No hay registros con respuestas de Check-in.")
        return

    # Date selection (single day) + filters (jugadora/turno)
    if "fecha" in d.columns and not d["fecha"].isna().all():
        min_date = d["fecha"].min().date()
        max_date = d["fecha"].max().date()
    else:
        st.info("No hay fechas válidas en los registros.")
        return

    with st.expander("Filtros", expanded=True):
        f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
        with f1:
            # Default to today if within range; else fall back to latest date with records
            today = date.today()
            default_date = today if (min_date <= today <= max_date) else max_date
            sel_date = st.date_input("Fecha", value=default_date, min_value=min_date, max_value=max_date)
        with f2:
            jugadores = (
                sorted(d["nombre_jugadora"].dropna().astype(str).unique().tolist())
                if "nombre_jugadora" in d.columns
                else []
            )
            jug_sel = st.multiselect("Jugadora(s)", options=jugadores, default=[])
        with f3:
            turnos = ["Turno 1", "Turno 2", "Turno 3"]
            if "turno" in d.columns:
                present = d["turno"].dropna().astype(str).unique().tolist()
                turnos = [t for t in turnos if t in present] or ["Turno 1", "Turno 2", "Turno 3"]
            turno_sel = st.multiselect("Turno(s)", options=turnos, default=[])
        with f4:
            ics_sel = st.multiselect("ICS", options=["ROJO", "AMARILLO", "VERDE"], default=[])

    day_mask = d["fecha"].dt.date == sel_date
    day_df = d[day_mask].copy()
    if 'jug_sel' in locals() and jug_sel:
        day_df = day_df[day_df["nombre_jugadora"].astype(str).isin(jug_sel)]
    if 'turno_sel' in locals() and turno_sel:
        day_df = day_df[day_df["turno"].astype(str).isin(turno_sel)]
    if day_df.empty:
        st.info("No hay registros para la fecha seleccionada.")
        return

    # Compute ICS (Indice de Componente Subjetivo)
    def _val_cat(v: float) -> str:
        try:
            v = float(v)
        except Exception:
            return ""
        if v in (1, 2):
            return "VERDE"
        if v == 3:
            return "AMARILLO"
        if v in (4, 5):
            return "ROJO"
        return ""

    def _compute_ics(row: pd.Series) -> str:
        keys = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
        # Ensure values
        if not all(k in row and pd.notna(row[k]) for k in keys):
            return ""
        cats = {k: _val_cat(row[k]) for k in keys}
        greens = sum(1 for c in cats.values() if c == "VERDE")
        yellows = [k for k, c in cats.items() if c == "AMARILLO"]
        reds = sum(1 for c in cats.values() if c == "ROJO")

        # ROJO conditions first
        if reds >= 1:
            return "ROJO"
        if len(yellows) >= 3:
            return "ROJO"
        if len(yellows) == 2 and ("dolor" in yellows):
            return "ROJO"

        # VERDE conditions
        if greens == 5:
            return "VERDE"
        if greens == 4 and len(yellows) == 1 and ("dolor" not in yellows):
            return "VERDE"

        # AMARILLO conditions
        if len(yellows) == 1:
            return "AMARILLO"
        if len(yellows) == 2 and ("dolor" not in yellows):
            return "AMARILLO"

        # Fallback
        return "AMARILLO" if len(yellows) > 0 else ""

    d["ICS"] = d.apply(_compute_ics, axis=1)

    # Select and rename columns
    cols = []
    def add_if(col):
        if col in day_df.columns:
            cols.append(col)

    add_if("nombre_jugadora")
    add_if("fecha_hora")
    add_if("periodizacion_tactica")
    add_if("recuperacion")
    add_if("fatiga")
    add_if("sueno")
    add_if("stress")
    add_if("dolor")
    add_if("partes_cuerpo_dolor")
    add_if("observacion")

    # ensure ICS is aligned to same rows
    day_df = day_df.merge(d[["fecha_hora", "id_jugadora", "ICS"]], on=["fecha_hora", "id_jugadora"], how="left") if "id_jugadora" in day_df.columns else day_df
    view = day_df[cols + (["ICS"] if "ICS" in day_df.columns else [])].copy()

    # Apply ICS filter if selected
    if 'ics_sel' in locals() and ics_sel and "ICS" in view.columns:
        view = view[view["ICS"].isin(ics_sel)]

    if view.empty:
        st.info("No hay registros que coincidan con los filtros.")
        return
    view = view.rename(columns={
        "nombre_jugadora": "Jugadora",
        "fecha_hora": "Fecha",
        "periodizacion_tactica": "Periodización",
        "recuperacion": "Recuperación",
        "fatiga": "Fatiga",
        "sueno": "Sueño",
        "stress": "Estrés",
        "dolor": "Dolor",
        "partes_cuerpo_dolor": "Partes con dolor",
        "observacion": "Observación",
        "ICS": "ICS",
    })

    # Counters by ICS
    if "ICS" in view.columns:
        counts = view["ICS"].value_counts()
        c_rojo = int(counts.get("ROJO", 0))
        c_amarillo = int(counts.get("AMARILLO", 0))
        c_verde = int(counts.get("VERDE", 0))
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("ROJO", value=c_rojo)
        with mc2:
            st.metric("AMARILLO", value=c_amarillo)
        with mc3:
            st.metric("VERDE", value=c_verde)

    # Sort by ICS severity then Jugadora
    if "ICS" in view.columns:
        order_map = {"ROJO": 0, "AMARILLO": 1, "VERDE": 2}
        view["_ics_order"] = view["ICS"].map(order_map).fillna(3)
        sort_by = ["_ics_order"] + (["Jugadora"] if "Jugadora" in view.columns else [])
        view = view.sort_values(sort_by, ascending=[True] + [True] * (len(sort_by) - 1))
        view = view.drop(columns=["_ics_order"])  # clean temporary column
    elif "Jugadora" in view.columns:
        view = view.sort_values("Jugadora")

    # Apply pastel colors to ICS column
    def _ics_style(val: str) -> str:
        if val == "VERDE":
            return "background-color: #d4edda; color: #155724;"
        if val == "AMARILLO":
            return "background-color: #fff3cd; color: #856404;"
        if val == "ROJO":
            return "background-color: #f8d7da; color: #721c24;"
        return ""

    if "ICS" in view.columns:
        styler = view.style.applymap(_ics_style, subset=["ICS"])  # type: ignore
        st.dataframe(styler, use_container_width=True)
    else:
        st.dataframe(view, use_container_width=True)

    # Downloads
    st.markdown("---")
    c1, c2 = st.columns(2)
    export_df = view.copy()
    # Stringify list column for CSV/JSONL
    if "Partes con dolor" in export_df.columns:
        export_df["Partes con dolor"] = export_df["Partes con dolor"].apply(
            lambda x: "; ".join(map(str, x)) if isinstance(x, (list, tuple)) else ("" if x is None else str(x))
        )
    with c1:
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV", data=csv_bytes, file_name=f"checkin_{sel_date}.csv", mime="text/csv")
    with c2:
        import json
        records = export_df.where(pd.notnull(export_df), None).to_dict(orient="records")
        jsonl_str = "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records)
        st.download_button(
            "Descargar JSONL",
            data=jsonl_str.encode("utf-8"),
            file_name=f"checkin_{sel_date}.jsonl",
            mime="application/json",
        )

    # Non-responding players for the selected date (considering optional Jugadora filter)
    st.markdown("---")
    st.subheader("Jugadoras que no respondieron")
    jug_df, jug_err = load_jugadoras()
    if jug_err or jug_df is None or jug_df.empty:
        st.info("No se pudo cargar el listado de jugadoras (data/jugadoras.xlsx).")
    else:
        roster = jug_df["nombre_jugadora"].astype(str).tolist()
        if 'jug_sel' in locals() and jug_sel:
            roster = [j for j in roster if j in jug_sel]
        responded = set(view["Jugadora"].astype(str).unique().tolist()) if "Jugadora" in view.columns else set()
        missing = [j for j in roster if j not in responded]
        if missing:
            st.dataframe(pd.DataFrame({"Jugadora": missing}).sort_values("Jugadora"), use_container_width=True)
        else:
            st.success("Todas las jugadoras seleccionadas respondieron en la fecha.")
