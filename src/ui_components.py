from typing import Dict, Tuple
from datetime import date

import pandas as pd
import altair as alt
import streamlit as st

from .io_files import get_template_bytes, load_jugadoras
from .schema import validate_checkin, validate_checkout
from .metrics import compute_rpe_metrics, RPEFilters

# Brand colors (Dux Logroño): grana primary and black text
BRAND_PRIMARY = "#800000"  # grana/maroon
BRAND_TEXT = "#000000"     # black

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

    # Minutos del día (suma) como KPI superior
    try:
        d_min = df.copy()
        if "tipo" in d_min.columns:
            d_min = d_min[d_min["tipo"] == "checkOut"]
        if "minutos_sesion" in d_min.columns:
            d_min["minutos_sesion"] = pd.to_numeric(d_min["minutos_sesion"], errors="coerce")
        else:
            d_min["minutos_sesion"] = pd.NA
        # fecha_dia
        if "fecha_dia" not in d_min.columns and "fecha" in d_min.columns:
            d_min["fecha_dia"] = pd.to_datetime(d_min["fecha"], errors="coerce").dt.date
        # Aplicar mismos filtros de arriba (jugadoras, turnos, rango)
        if 'jug_sel' in locals() and jug_sel:
            d_min = d_min[d_min["nombre_jugadora"].astype(str).isin(jug_sel)]
        if 'turno_sel' in locals() and turno_sel:
            d_min = d_min[d_min["turno"].astype(str).isin(turno_sel)]
        if 'start' in locals() and 'end' in locals() and start and end and "fecha_dia" in d_min.columns:
            mask = (d_min["fecha_dia"] >= start) & (d_min["fecha_dia"] <= end)
            d_min = d_min[mask]
        # Determinar end_day igual que en métricas
        daily_tbl = metrics.get("daily_table")
        end_day = None
        if isinstance(daily_tbl, pd.DataFrame) and not daily_tbl.empty:
            end_day = daily_tbl["fecha_dia"].max()
        if end_day is not None and "fecha_dia" in d_min.columns:
            minutos_dia = d_min.loc[d_min["fecha_dia"] == end_day, "minutos_sesion"].sum()
            st.metric("Minutos día", value=(f"{minutos_dia:.0f}" if pd.notna(minutos_dia) else "-"))
    except Exception:
        pass

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

    # --- Gráficas por jugadora ---
    st.markdown("---")
    st.subheader("Gráficas por jugadora")
    # Controles de visualización y orden
    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
    with ctrl1:
        chart_type = st.radio("Gráfico", options=["RPE", "UA"], horizontal=True)
    with ctrl2:
        sort_key = st.selectbox("Ordenar por", options=["UA total", "Nombre"], index=0)
    with ctrl3:
        sort_order = st.selectbox("Orden", options=["Descendente", "Ascendente"], index=0)
    try:
        if df is None or df.empty:
            st.info("No hay registros para graficar.")
            return

        d = df.copy()
        # Mantener sólo Check-out
        if "tipo" in d.columns:
            d = d[d["tipo"] == "checkOut"]
        # Asegurar columnas numéricas
        if "rpe" in d.columns:
            d["rpe"] = pd.to_numeric(d["rpe"], errors="coerce")
        else:
            d["rpe"] = pd.NA
        if "ua" in d.columns:
            d["ua"] = pd.to_numeric(d["ua"], errors="coerce")
        else:
            d["ua"] = pd.NA
        if "minutos_sesion" in d.columns:
            d["minutos_sesion"] = pd.to_numeric(d["minutos_sesion"], errors="coerce")
        else:
            d["minutos_sesion"] = pd.NA
        # Crear fecha_dia si no existe
        if "fecha_dia" not in d.columns:
            if "fecha" in d.columns:
                d["fecha_dia"] = pd.to_datetime(d["fecha"], errors="coerce").dt.date
        d = d.dropna(subset=["fecha_dia"]) if "fecha_dia" in d.columns else d

        # Aplicar filtros de fecha y turno, pero NO filtrar por jugadoras para la media del equipo
        # Fecha
        if 'start' in locals() and 'end' in locals() and start and end and "fecha_dia" in d.columns:
            mask = (d["fecha_dia"] >= start) & (d["fecha_dia"] <= end)
            d = d[mask]
        # Turno
        if 'turno_sel' in locals() and turno_sel:
            d = d[d["turno"].astype(str).isin(turno_sel)]

        if d.empty or "nombre_jugadora" not in d.columns:
            st.info("No hay datos válidos para graficar.")
            return

        # Agregar por jugadora y día: RPE medio y UA total
        per_player_day = (
            d.groupby(["fecha_dia", "nombre_jugadora"], as_index=False)
            .agg({"rpe": "mean", "ua": "sum"})
        )

        # Promedio del equipo por día (promedio entre jugadoras ese día)
        team_daily = (
            per_player_day.groupby("fecha_dia", as_index=False)
            .agg({"rpe": "mean", "ua": "mean"})
            .rename(columns={"rpe": "team_rpe_avg", "ua": "team_ua_avg"})
        )

        # Determinar jugadoras a mostrar y ordenarlas
        all_players = per_player_day["nombre_jugadora"].astype(str).unique().tolist()
        if 'jug_sel' in locals() and jug_sel:
            players = [p for p in all_players if p in jug_sel]
        else:
            players = sorted(all_players)

        # Cálculo de UA total por jugadora para ordenar si corresponde
        ua_totals = per_player_day.groupby("nombre_jugadora", as_index=False)["ua"].sum().rename(columns={"ua": "ua_total"})
        # Construir dataframe de orden
        order_df = pd.DataFrame({"nombre_jugadora": players})
        order_df = order_df.merge(ua_totals, on="nombre_jugadora", how="left")
        order_df["ua_total"] = pd.to_numeric(order_df["ua_total"], errors="coerce").fillna(0)
        if sort_key == "UA total":
            ascending = (sort_order == "Ascendente")
            order_df = order_df.sort_values(["ua_total", "nombre_jugadora"], ascending=[ascending, True])
        else:  # Nombre
            ascending = (sort_order == "Ascendente")
            order_df = order_df.sort_values(["nombre_jugadora"], ascending=[ascending])
        selected_players = order_df["nombre_jugadora"].tolist()

        # Convertir fecha a datetime para ejes ordenados en Altair
        per_player_day = per_player_day.copy()
        team_daily = team_daily.copy()
        per_player_day["fecha_dia_dt"] = pd.to_datetime(per_player_day["fecha_dia"])  # type: ignore
        team_daily["fecha_dia_dt"] = pd.to_datetime(team_daily["fecha_dia"])  # type: ignore

        # Dibujar por jugadora
        for player in selected_players:
            st.markdown(f"#### {player}")
            p_df = per_player_day[per_player_day["nombre_jugadora"].astype(str) == str(player)]
            if p_df.empty:
                st.info("Sin datos en el rango para esta jugadora.")
                continue
            # Join con promedio del equipo
            plot_df = p_df.merge(team_daily[["fecha_dia_dt", "team_rpe_avg", "team_ua_avg"]], on="fecha_dia_dt", how="left")

            # RPE: barras (jugadora) + línea (promedio equipo)
            base_rpe = alt.Chart(plot_df).encode(
                x=alt.X("fecha_dia_dt:T", title="Fecha"),
            )
            bars_rpe = base_rpe.mark_bar(color=BRAND_PRIMARY).encode(
                y=alt.Y("rpe:Q", title="RPE diario (media)"),
                tooltip=["fecha_dia_dt:T", alt.Tooltip("rpe:Q", format=".2f", title="RPE jugadora"), alt.Tooltip("team_rpe_avg:Q", format=".2f", title="RPE promedio equipo")],
            )
            line_rpe = base_rpe.mark_line(color=BRAND_TEXT, point=True).encode(
                y=alt.Y("team_rpe_avg:Q", title="RPE promedio equipo"),
            )
            if chart_type == "RPE":
                chart_rpe = alt.layer(bars_rpe, line_rpe).resolve_scale(y='independent').properties(height=220, width="container")
                st.altair_chart(chart_rpe, use_container_width=True)

            # UA: barras (jugadora) + línea (promedio equipo)
            base_ua = alt.Chart(plot_df).encode(
                x=alt.X("fecha_dia_dt:T", title="Fecha"),
            )
            bars_ua = base_ua.mark_bar(color=BRAND_PRIMARY).encode(
                y=alt.Y("ua:Q", title="UA diario (suma)"),
                tooltip=["fecha_dia_dt:T", alt.Tooltip("ua:Q", format=".0f", title="UA jugadora"), alt.Tooltip("team_ua_avg:Q", format=".0f", title="UA promedio equipo")],
            )
            line_ua = base_ua.mark_line(color=BRAND_TEXT, point=True).encode(
                y=alt.Y("team_ua_avg:Q", title="UA promedio equipo"),
            )
            if chart_type == "UA":
                chart_ua = alt.layer(bars_ua, line_ua).resolve_scale(y='independent').properties(height=220, width="container")
                st.altair_chart(chart_ua, use_container_width=True)

            # ACWR (agudo:crónico) por día con zonas 'sweet spot' y 'danger zone'
            try:
                acwr_src = p_df.sort_values("fecha_dia_dt").copy()
                # Rolling promedios (agudo: 7 días; crónico: 28 días)
                acwr_src["ua"] = pd.to_numeric(acwr_src["ua"], errors="coerce")
                acwr_src["acute_mean7"] = acwr_src["ua"].rolling(7, min_periods=3).mean()
                acwr_src["chronic_mean28"] = acwr_src["ua"].rolling(28, min_periods=7).mean()
                acwr_src["acwr"] = acwr_src["acute_mean7"] / acwr_src["chronic_mean28"]
                acwr_src = acwr_src.dropna(subset=["acwr"])  # necesita suficientes días

                if not acwr_src.empty:
                    # Clasificación de zonas para colorear puntos
                    def _zone(v: float) -> str:
                        try:
                            if v < 0.8:
                                return "Baja"
                            if 0.8 <= v < 1.3:
                                return "Sweet Spot"
                            if v >= 1.5:
                                return "Danger Zone"
                            return "Elevada"
                        except Exception:
                            return ""

                    acwr_src["zona"] = acwr_src["acwr"].apply(_zone)

                    # Fondos: verde para 0.8-1.3, rojo para >1.5
                    bg_green = alt.Chart(pd.DataFrame({"y0": [0.8], "y1": [1.3]})).mark_rect(color="#d4edda", opacity=0.6)
                    bg_red = alt.Chart(pd.DataFrame({"y0": [1.5], "y1": [3.0]})).mark_rect(color="#f8d7da", opacity=0.6)

                    # Reglas de referencia
                    rules = alt.Chart(pd.DataFrame({"y": [0.8, 1.3, 1.5]})).mark_rule(color=BRAND_TEXT, strokeDash=[4,2], opacity=0.6).encode(y="y:Q")

                    base_acwr = alt.Chart(acwr_src).encode(
                        x=alt.X("fecha_dia_dt:T", title="Fecha"),
                        y=alt.Y("acwr:Q", title="ACWR (agudo:crónico)", scale=alt.Scale(domain=[0, max(2.5, float(acwr_src['acwr'].max()) + 0.2)])),
                    )
                    pts = base_acwr.mark_circle(size=60).encode(color=alt.Color("zona:N", scale=alt.Scale(domain=["Sweet Spot", "Baja", "Elevada", "Danger Zone"], range=["#2ca25f", "#9ecae1", "#fdae6b", "#d62728"]), title="Zona"), tooltip=["fecha_dia_dt:T", alt.Tooltip("acwr:Q", format=".2f")])
                    line = base_acwr.mark_line(color=BRAND_TEXT)

                    # Para que los rectángulos cubran todo el eje X, damos una escala X con domain igual al de los datos
                    x_domain = {
                        "values": acwr_src["fecha_dia_dt"].sort_values().astype("datetime64[ns]").tolist()
                    }
                    bg_green = bg_green.encode(y="y0:Q", y2="y1:Q").properties()
                    bg_red = bg_red.encode(y="y0:Q", y2="y1:Q").properties()

                    chart_acwr = alt.layer(bg_green, bg_red, rules, line, pts).resolve_scale(y="shared").properties(height=220, width="container")
                    st.altair_chart(chart_acwr, use_container_width=True)
            except Exception:
                pass
    except Exception:
        # Evitar que un problema con las gráficas rompa toda la vista
        st.info("No se pudieron renderizar las gráficas por jugadora.")


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

    # --- Gráfica por jugadora (día seleccionado) con línea de promedio del equipo ---
    st.markdown("---")
    st.subheader("Gráfica por jugadora (Check-in)")
    # Controles: métrica, ordenación
    cc1, cc2, cc3 = st.columns([1, 1, 1])
    with cc1:
        metric_opt = st.selectbox(
            "Métrica",
            options=["recuperacion", "fatiga", "sueno", "stress", "dolor"],
            format_func=lambda x: {"recuperacion": "Recuperación", "fatiga": "Fatiga", "sueno": "Sueño", "stress": "Estrés", "dolor": "Dolor"}[x],
        )
    with cc2:
        sort_key = st.selectbox("Ordenar por", options=["Valor", "Nombre"], index=0)
    with cc3:
        sort_order = st.selectbox("Orden", options=["Descendente", "Ascendente"], index=0)

    try:
        # Usar day_df (datos crudos del día seleccionado) para conservar numéricos
        plot_src = day_df.copy()
        if metric_opt not in plot_src.columns or "nombre_jugadora" not in plot_src.columns:
            st.info("No hay datos suficientes para graficar.")
            return
        plot_src = plot_src[["nombre_jugadora", metric_opt]].dropna()
        plot_src[metric_opt] = pd.to_numeric(plot_src[metric_opt], errors="coerce")
        plot_src = plot_src.dropna()
        if plot_src.empty:
            st.info("No hay valores para la métrica seleccionada.")
            return
        # Agregar por jugadora por si hubiese múltiples registros; tomar media por jugadora el día
        g = plot_src.groupby("nombre_jugadora", as_index=False)[metric_opt].mean().rename(columns={metric_opt: "valor"})
        # Orden
        ascending = (sort_order == "Ascendente")
        if sort_key == "Valor":
            g = g.sort_values(["valor", "nombre_jugadora"], ascending=[ascending, True])
        else:
            g = g.sort_values(["nombre_jugadora"], ascending=[ascending])
        team_avg = float(g["valor"].mean()) if not g.empty else None

        # Altair chart: barras por jugadora + línea horizontal promedio equipo
        chart = alt.Chart(g).encode(
            x=alt.X("nombre_jugadora:N", title="Jugadora", sort=g["nombre_jugadora"].tolist()),
            y=alt.Y("valor:Q", title=f"{metric_opt.capitalize()} (1-5)"),
            tooltip=["nombre_jugadora:N", alt.Tooltip("valor:Q", format=".2f", title="Valor")],
        )
        bars = chart.mark_bar(color=BRAND_PRIMARY)
        if team_avg is not None:
            rule = alt.Chart(pd.DataFrame({"y": [team_avg]})).mark_rule(color=BRAND_TEXT).encode(y="y:Q")
            st.altair_chart(bars + rule, use_container_width=True)
        else:
            st.altair_chart(bars, use_container_width=True)
    except Exception:
        st.info("No se pudo renderizar la gráfica por jugadora.")

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


def individual_report_view(df: pd.DataFrame) -> None:
    st.subheader("Reporte individual")
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return
    d = df.copy()
    # Asegurar columnas de fecha
    if "fecha" not in d.columns and "fecha_hora" in d.columns:
        d["fecha"] = pd.to_datetime(d["fecha_hora"], errors="coerce")
    if "fecha_dia" not in d.columns and "fecha" in d.columns:
        d["fecha_dia"] = d["fecha"].dt.date

    jugadores = (
        sorted(d["nombre_jugadora"].dropna().astype(str).unique().tolist())
        if "nombre_jugadora" in d.columns
        else []
    )
    if not jugadores:
        st.info("No hay jugadoras en los registros.")
        return

    c1, c2 = st.columns([1, 1])
    with c1:
        player = st.selectbox("Jugadora", options=jugadores, index=0)
    with c2:
        # Rango de fechas predeterminado al rango completo de la jugadora
        d_player = d[d["nombre_jugadora"].astype(str) == str(player)]
        if "fecha_dia" in d_player.columns and not d_player["fecha_dia"].isna().all():
            min_date = d_player["fecha_dia"].min()
            max_date = d_player["fecha_dia"].max()
            start, end = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        else:
            start = end = None

    # Filtrar por jugadora y rango
    d = d_player.copy()
    if start and end and "fecha_dia" in d.columns:
        mask = (d["fecha_dia"] >= start) & (d["fecha_dia"] <= end)
        d = d[mask]

    if d.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    # Resumen rápido
    st.markdown("---")
    st.subheader("Resumen")
    # Check-in: medias por métrica 1..5
    checkin_fields = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
    means = {k: float(pd.to_numeric(d[k], errors="coerce").mean()) if k in d.columns else None for k in checkin_fields}
    colA, colB, colC, colD, colE = st.columns(5)
    colA.metric("Recuperación media", f"{means.get('recuperacion', 0):.2f}" if means.get('recuperacion') is not None else "-")
    colB.metric("Fatiga media", f"{means.get('fatiga', 0):.2f}" if means.get('fatiga') is not None else "-")
    colC.metric("Sueño medio", f"{means.get('sueno', 0):.2f}" if means.get('sueno') is not None else "-")
    colD.metric("Estrés medio", f"{means.get('stress', 0):.2f}" if means.get('stress') is not None else "-")
    colE.metric("Dolor medio", f"{means.get('dolor', 0):.2f}" if means.get('dolor') is not None else "-")

    # Check-out: totales / medias
    m_cols = st.columns(3)
    with m_cols[0]:
        ua_total = float(pd.to_numeric(d.get("ua"), errors="coerce").sum()) if "ua" in d.columns else None
        st.metric("UA total", f"{ua_total:.0f}" if ua_total is not None else "-")
    with m_cols[1]:
        min_total = float(pd.to_numeric(d.get("minutos_sesion"), errors="coerce").sum()) if "minutos_sesion" in d.columns else None
        st.metric("Minutos totales", f"{min_total:.0f}" if min_total is not None else "-")
    with m_cols[2]:
        rpe_media = float(pd.to_numeric(d.get("rpe"), errors="coerce").mean()) if "rpe" in d.columns else None
        st.metric("RPE medio", f"{rpe_media:.2f}" if rpe_media is not None else "-")

    # Gráficas
    st.markdown("---")
    st.subheader("Evolución en el tiempo")
    # Preparar dataframe temporal
    t = d.copy()
    t = t.sort_values("fecha") if "fecha" in t.columns else t
    if "fecha" not in t.columns:
        st.info("No hay fechas válidas para graficar.")
        return
    # Check-in: barras por métrica (selector) + línea de promedio del equipo + barras de desviación estándar (rolling 7d)
    ci_metrics = [c for c in checkin_fields if c in t.columns]
    if ci_metrics:
        sel_col1, _ = st.columns([1, 3])
        with sel_col1:
            ci_metric = st.selectbox(
                "Métrica de Check-in",
                options=ci_metrics,
                format_func=lambda x: {"recuperacion": "Recuperación", "fatiga": "Fatiga", "sueno": "Sueño", "stress": "Estrés", "dolor": "Dolor"}.get(x, x),
            )

        # Serie de la jugadora
        df_p = t[["fecha", ci_metric]].dropna().copy()
        df_p[ci_metric] = pd.to_numeric(df_p[ci_metric], errors="coerce")
        df_p = df_p.dropna()
        if not df_p.empty:
            # Rolling std 7 días (mínimo 2)
            df_p = df_p.sort_values("fecha")
            df_p["std7"] = df_p[ci_metric].rolling(7, min_periods=2).std()
            df_p["yLow"] = (df_p[ci_metric] - df_p["std7"]).clip(lower=1, upper=5)
            df_p["yHigh"] = (df_p[ci_metric] + df_p["std7"]).clip(lower=1, upper=5)

            # Promedio del equipo por día en el mismo rango (manejo robusto de fechas)
            team_all = df.copy()
            if "fecha" not in team_all.columns and "fecha_hora" in team_all.columns:
                team_all["fecha"] = pd.to_datetime(team_all["fecha_hora"], errors="coerce")
            if "fecha" in team_all.columns:
                team_all = team_all.dropna(subset=["fecha"]).copy()
                if start and end:
                    team_all = team_all[(team_all["fecha"].dt.date >= start) & (team_all["fecha"].dt.date <= end)]
                team_all[ci_metric] = pd.to_numeric(team_all.get(ci_metric), errors="coerce")
                team_all["fecha_day"] = team_all["fecha"].dt.date
                team_all = team_all.dropna(subset=["fecha_day"])  # seguridad
                team_daily = team_all.groupby("fecha_day", as_index=False)[ci_metric].mean().rename(columns={ci_metric: "team_avg"})
                team_daily["fecha"] = pd.to_datetime(team_daily["fecha_day"])
            else:
                team_daily = pd.DataFrame(columns=["fecha", "team_avg"])  

            plot_df = df_p.merge(team_daily[["fecha", "team_avg"]], on="fecha", how="left")

            base_ci = alt.Chart(plot_df).encode(x=alt.X("fecha:T", title="Fecha"))
            bars_ci = base_ci.mark_bar(color=BRAND_PRIMARY).encode(y=alt.Y(f"{ci_metric}:Q", title="Check-in (1-5)"), tooltip=["fecha:T", alt.Tooltip(f"{ci_metric}:Q", format=".2f", title="Valor jugadora"), alt.Tooltip("team_avg:Q", format=".2f", title="Promedio equipo")])
            err_ci = base_ci.mark_errorbar(color=BRAND_TEXT, opacity=0.8).encode(y=alt.Y("yLow:Q"), y2="yHigh:Q")
            line_ci = base_ci.mark_line(color=BRAND_TEXT).encode(y=alt.Y("team_avg:Q", title="Promedio equipo"))
            st.altair_chart(alt.layer(bars_ci, err_ci, line_ci).properties(height=280), use_container_width=True)

    # Check-out: UA, RPE, minutos en líneas separadas
    co_cols = st.columns(3)
    with co_cols[0]:
        if "ua" in t.columns:
            co_ua = t[["fecha", "ua"]].copy()
            co_ua["ua"] = pd.to_numeric(co_ua["ua"], errors="coerce")
            co_ua = co_ua.dropna().sort_values("fecha")
            co_ua["std7"] = co_ua["ua"].rolling(7, min_periods=2).std()
            co_ua["yLow"] = (co_ua["ua"] - co_ua["std7"]).clip(lower=0)
            co_ua["yHigh"] = (co_ua["ua"] + co_ua["std7"]).clip(lower=0)

            team_all = df.copy()
            if "fecha" not in team_all.columns and "fecha_hora" in team_all.columns:
                team_all["fecha"] = pd.to_datetime(team_all["fecha_hora"], errors="coerce")
            if "fecha" in team_all.columns:
                team_all = team_all.dropna(subset=["fecha"]).copy()
                if start and end:
                    team_all = team_all[(team_all["fecha"].dt.date >= start) & (team_all["fecha"].dt.date <= end)]
                team_all["ua"] = pd.to_numeric(team_all.get("ua"), errors="coerce")
                team_all["fecha_day"] = team_all["fecha"].dt.date
                team_all = team_all.dropna(subset=["fecha_day"])  
                team_daily = team_all.groupby("fecha_day", as_index=False)["ua"].mean().rename(columns={"ua": "team_avg"})
                team_daily["fecha"] = pd.to_datetime(team_daily["fecha_day"])
            else:
                team_daily = pd.DataFrame(columns=["fecha", "team_avg"])  
            plot_df = co_ua.merge(team_daily[["fecha", "team_avg"]], on="fecha", how="left")

            base = alt.Chart(plot_df).encode(x=alt.X("fecha:T", title="Fecha"))
            bars = base.mark_bar(color=BRAND_PRIMARY).encode(y=alt.Y("ua:Q", title="UA"), tooltip=["fecha:T", alt.Tooltip("ua:Q", format=".0f", title="UA jugadora"), alt.Tooltip("team_avg:Q", format=".0f", title="Promedio equipo")])
            err = base.mark_errorbar(color=BRAND_TEXT, opacity=0.8).encode(y="yLow:Q", y2="yHigh:Q")
            line = base.mark_line(color=BRAND_TEXT).encode(y=alt.Y("team_avg:Q", title="Promedio equipo"))
            st.altair_chart(alt.layer(bars, err, line).properties(height=220), use_container_width=True)
    with co_cols[1]:
        if "rpe" in t.columns:
            co_rpe = t[["fecha", "rpe"]].copy()
            co_rpe["rpe"] = pd.to_numeric(co_rpe["rpe"], errors="coerce")
            co_rpe = co_rpe.dropna().sort_values("fecha")
            co_rpe["std7"] = co_rpe["rpe"].rolling(7, min_periods=2).std()
            co_rpe["yLow"] = (co_rpe["rpe"] - co_rpe["std7"]).clip(lower=1, upper=10)
            co_rpe["yHigh"] = (co_rpe["rpe"] + co_rpe["std7"]).clip(lower=1, upper=10)

            team_all = df.copy()
            if "fecha" not in team_all.columns and "fecha_hora" in team_all.columns:
                team_all["fecha"] = pd.to_datetime(team_all["fecha_hora"], errors="coerce")
            if "fecha" in team_all.columns:
                team_all = team_all.dropna(subset=["fecha"]).copy()
                if start and end:
                    team_all = team_all[(team_all["fecha"].dt.date >= start) & (team_all["fecha"].dt.date <= end)]
                team_all["rpe"] = pd.to_numeric(team_all.get("rpe"), errors="coerce")
                team_all["fecha_day"] = team_all["fecha"].dt.date
                team_all = team_all.dropna(subset=["fecha_day"])  
                team_daily = team_all.groupby("fecha_day", as_index=False)["rpe"].mean().rename(columns={"rpe": "team_avg"})
                team_daily["fecha"] = pd.to_datetime(team_daily["fecha_day"])
            else:
                team_daily = pd.DataFrame(columns=["fecha", "team_avg"])  
            plot_df = co_rpe.merge(team_daily[["fecha", "team_avg"]], on="fecha", how="left")

            base = alt.Chart(plot_df).encode(x=alt.X("fecha:T", title="Fecha"))
            bars = base.mark_bar(color=BRAND_PRIMARY).encode(y=alt.Y("rpe:Q", title="RPE"), tooltip=["fecha:T", alt.Tooltip("rpe:Q", format=".2f", title="RPE jugadora"), alt.Tooltip("team_avg:Q", format=".2f", title="Promedio equipo")])
            err = base.mark_errorbar(color=BRAND_TEXT, opacity=0.8).encode(y="yLow:Q", y2="yHigh:Q")
            line = base.mark_line(color=BRAND_TEXT).encode(y=alt.Y("team_avg:Q", title="Promedio equipo"))
            st.altair_chart(alt.layer(bars, err, line).properties(height=220), use_container_width=True)
    with co_cols[2]:
        if "minutos_sesion" in t.columns:
            co_min = t[["fecha", "minutos_sesion"]].copy()
            co_min["minutos_sesion"] = pd.to_numeric(co_min["minutos_sesion"], errors="coerce")
            co_min = co_min.dropna().sort_values("fecha")
            co_min["std7"] = co_min["minutos_sesion"].rolling(7, min_periods=2).std()
            co_min["yLow"] = (co_min["minutos_sesion"] - co_min["std7"]).clip(lower=0)
            co_min["yHigh"] = (co_min["minutos_sesion"] + co_min["std7"]).clip(lower=0)

            team_all = df.copy()
            if "fecha" not in team_all.columns and "fecha_hora" in team_all.columns:
                team_all["fecha"] = pd.to_datetime(team_all["fecha_hora"], errors="coerce")
            if "fecha" in team_all.columns:
                team_all = team_all.dropna(subset=["fecha"]).copy()
                if start and end:
                    team_all = team_all[(team_all["fecha"].dt.date >= start) & (team_all["fecha"].dt.date <= end)]
                team_all["minutos_sesion"] = pd.to_numeric(team_all.get("minutos_sesion"), errors="coerce")
                team_all["fecha_day"] = team_all["fecha"].dt.date
                team_all = team_all.dropna(subset=["fecha_day"])  
                team_daily = team_all.groupby("fecha_day", as_index=False)["minutos_sesion"].mean().rename(columns={"minutos_sesion": "team_avg"})
                team_daily["fecha"] = pd.to_datetime(team_daily["fecha_day"])
            else:
                team_daily = pd.DataFrame(columns=["fecha", "team_avg"])  
            plot_df = co_min.merge(team_daily[["fecha", "team_avg"]], on="fecha", how="left")

            base = alt.Chart(plot_df).encode(x=alt.X("fecha:T", title="Fecha"))
            bars = base.mark_bar(color=BRAND_PRIMARY).encode(y=alt.Y("minutos_sesion:Q", title="Minutos"), tooltip=["fecha:T", alt.Tooltip("minutos_sesion:Q", format=".0f", title="Minutos jugadora"), alt.Tooltip("team_avg:Q", format=".0f", title="Promedio equipo")])
            err = base.mark_errorbar(color=BRAND_TEXT, opacity=0.8).encode(y="yLow:Q", y2="yHigh:Q")
            line = base.mark_line(color=BRAND_TEXT).encode(y=alt.Y("team_avg:Q", title="Promedio equipo"))
            st.altair_chart(alt.layer(bars, err, line).properties(height=220), use_container_width=True)

