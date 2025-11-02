from datetime import date

import pandas as pd
import altair as alt
import streamlit as st
import datetime

from .metrics import compute_rpe_metrics, RPEFilters
from src.db_records import load_jugadoras_db, load_competiciones_db

# Brand colors (Dux Logroño): grana primary and black text
BRAND_PRIMARY = "#800000"  # grana/maroon
BRAND_TEXT = "#000000"     # black

def _exportable_chart(chart: alt.Chart, key: str, height: int = 300):
    """Render Altair chart with a small export UI (PNG) via vega-embed actions.

    This renders an additional lightweight copy of the chart below the Streamlit chart
    that exposes the vega-embed toolbar with 'Export' enabled.
    """
    try:
        spec = chart.to_json()
        html = f"""
        <div id="{key}" style="width:100%"></div>
        <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
        <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
        <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
        <script>
          const spec = {spec};
          vegaEmbed('#{key}', spec, {{ actions: {{ export: true, source: false, editor: false, compiled: false }} }});
        </script>
        """
        components.html(html, height=height + 60)
    except Exception:
        # Fallback: no-op if export failed
        pass


def selection_header(jug_df: pd.DataFrame, comp_df: pd.DataFrame, modo: str = "registros"):

    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 2])

    with col1:
        competiciones_options = comp_df.to_dict("records")
        competicion = st.selectbox(
            "Plantel",
            options=competiciones_options,
            format_func=lambda x: f'{x["nombre"]} ({x["codigo"]})',
            placeholder="Seleccione una Competición",
            index=3
        )
    with col2:
        jugadora_opt = None
        if jug_df is not None and len(jug_df) > 0:
            if competicion:
                codigo_competicion = competicion["codigo"]
                jug_df_filtrado = jug_df[jug_df["plantel"] == codigo_competicion]

                # Convertir el DataFrame filtrado a lista de opciones
                jugadoras_filtradas = jug_df_filtrado.to_dict("records")
            else:
                jugadoras_filtradas = jug_df.to_dict("records")

            # La nueva columna para el identificacion de la jugadora
            jugadora_opt = st.selectbox(
                "Jugadora",
                options=jugadoras_filtradas,
                format_func=lambda x: f'{jugadoras_filtradas.index(x) + 1} - {x["nombre"]} {x["apellido"]}',
                placeholder="Seleccione una Jugadora",
                index=None
            )
        else:
            st.warning("No hay jugadoras cargadas.")
    
    with col3:
        turno = st.selectbox(
            "Turno",
            options=["Turno 1", "Turno 2", "Turno 3"],
            index=0)    
    
    tipo = None
    if modo == "registros":
        with col4:
            tipo = st.radio("Tipo de registro", options=["Check-in", "Check-out"], horizontal=True)

    start, end = None, None
    if modo == "reporte":
        with col4:
            # --- Rango permitido: últimos 15 días hasta hoy ---
            hoy = datetime.date.today()
            hace_15_dias = hoy - datetime.timedelta(days=15)

            # --- Definir valores por defecto ---
            start_default = hace_15_dias
            end_default = hoy

            start, end = st.date_input(
                "Rango de fechas", value=(start_default, end_default),
                min_value=hace_15_dias,
                max_value=hoy
            )

    return jugadora_opt, tipo, turno, start, end

def preview_record(record: dict) -> None:
    #st.subheader("Previsualización")
    # Header with key fields
    jug = record.get("identificacion", "-")
    fecha = record.get("fecha_sesion", "-")
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
    #st.subheader("Respuestas registradas")
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return

    # Filters
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            jugadores = sorted(df["identificacion"].dropna().astype(str).unique().tolist()) if "identificacion" in df.columns else []
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
        filtered = filtered[filtered["identificacion"].astype(str).isin(jug_sel)]
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
    st.dataframe(to_show)

    # Downloads
    st.divider()
    c1, c2 = st.columns(2)
    # Prepare export-friendly DataFrame: stringify timestamps/dates and replace NaNs
    export_df = filtered.copy()
    if "fecha" in export_df.columns:
        try:
            export_df["fecha"] = export_df["fecha"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            export_df["fecha"] = export_df["fecha"].astype(str)
    if "fecha_sesion" in export_df.columns:
        export_df["fecha_sesion"] = export_df["fecha_sesion"].astype(str)

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


def rpe_view(df: pd.DataFrame, jug_sel, turno_sel, start, end) -> None:
    #st.subheader("RPE / Cargas")
    if df is None or df.empty:
        st.info("No hay registros aún (se requieren Check-out con UA calculado).")
        return

    flt = RPEFilters(jugadores=jug_sel or None, turnos=turno_sel or None, start=start, end=end)
    #st.text(flt)
    metrics = compute_rpe_metrics(df, flt)

    st.subheader("Resumen")
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
        # fecha_sesion
        if "fecha_sesion" not in d_min.columns and "fecha" in d_min.columns:
            d_min["fecha_sesion"] = pd.to_datetime(d_min["fecha"], errors="coerce").dt.date
        # Aplicar mismos filtros de arriba (jugadoras, turnos, rango)
        if 'jug_sel' in locals() and jug_sel:
            d_min = d_min[d_min["identificacion"].astype(str).isin(jug_sel)]
        if 'turno_sel' in locals() and turno_sel:
            d_min = d_min[d_min["turno"].astype(str).isin(turno_sel)]
        if 'start' in locals() and 'end' in locals() and start and end and "fecha_sesion" in d_min.columns:
            mask = (d_min["fecha_sesion"] >= start) & (d_min["fecha_sesion"] <= end)
            d_min = d_min[mask]
        # Determinar end_day igual que en métricas
        daily_tbl = metrics.get("daily_table")
        end_day = None
        if isinstance(daily_tbl, pd.DataFrame) and not daily_tbl.empty:
            end_day = daily_tbl["fecha_sesion"].max()
        if end_day is not None and "fecha_sesion" in d_min.columns:
            minutos_dia = d_min.loc[d_min["fecha_sesion"] == end_day, "minutos_sesion"].sum()
            with k1:
                st.metric("Minutos día", value=(f"{minutos_dia:.0f}" if pd.notna(minutos_dia) else "-"))
    except Exception:
        pass

    #c5, c6, c7 = st.columns(3)
    with k2:
        st.metric("ACWR (aguda:crónica)", value=(f"{metrics['acwr']:.2f}" if metrics["acwr"] is not None else "-"))
    with k3:
        st.metric("Adaptación", value=(f"{metrics['adaptacion']:.2f}" if metrics["adaptacion"] is not None else "-"))
    with k4:
        st.metric("Variabilidad semana (std)", value=(f"{metrics['variabilidad_semana']:.2f}" if metrics["variabilidad_semana"] is not None else "-"))

    st.divider()
    st.caption("Cargas diarias (UA total por día)")
    daily = metrics.get("daily_table")
    if isinstance(daily, pd.DataFrame) and not daily.empty:
        st.dataframe(daily.sort_values("fecha_sesion"))
        st.divider()
        try:
            chart_df = daily.copy()
            chart_df = chart_df.rename(columns={"fecha_sesion": "Fecha", "ua_total": "UA"})
            chart_df = chart_df.set_index("Fecha")
            st.line_chart(chart_df["UA"])
        except Exception:
            pass
    else:
        st.info("No hay datos de Check-out con UA en el rango/criterios seleccionados.")

    # --- Gráficas por jugadora ---
    st.divider()
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
        # Crear fecha_sesion si no existe
        if "fecha_sesion" not in d.columns:
            if "fecha" in d.columns:
                d["fecha_sesion"] = pd.to_datetime(d["fecha"], errors="coerce").dt.date
        d = d.dropna(subset=["fecha_sesion"]) if "fecha_sesion" in d.columns else d

        # Aplicar filtros de fecha y turno, pero NO filtrar por jugadoras para la media del equipo
        # Fecha
        if 'start' in locals() and 'end' in locals() and start and end and "fecha_sesion" in d.columns:
            mask = (d["fecha_sesion"] >= start) & (d["fecha_sesion"] <= end)
            d = d[mask]
        # Turno
        if 'turno_sel' in locals() and turno_sel:
            d = d[d["turno"].astype(str).isin(turno_sel)]

        if d.empty or "identificacion" not in d.columns:
            st.info("No hay datos válidos para graficar.")
            return

        # Agregar por jugadora y día: RPE medio, UA total y PT (si existe)
        per_player_day = (
            d.groupby(["fecha_sesion", "identificacion"], as_index=False)
            .agg({"rpe": "mean", "ua": "sum"})
        )
        if "periodizacion_tactica" in d.columns:
            try:
                d_pt = d.copy()
                d_pt["periodizacion_tactica"] = pd.to_numeric(d_pt["periodizacion_tactica"], errors="coerce")
                pt_grp = d_pt.groupby(["fecha_sesion", "identificacion"], as_index=False)["periodizacion_tactica"].mean()
                pt_grp = pt_grp.rename(columns={"periodizacion_tactica": "pt"})
                per_player_day = per_player_day.merge(pt_grp, on=["fecha_sesion", "identificacion"], how="left")
            except Exception:
                pass

        # Promedio del equipo por día (promedio entre jugadoras ese día)
        team_daily = (
            per_player_day.groupby("fecha_sesion", as_index=False)
            .agg({"rpe": "mean", "ua": "mean"})
        )

        # Determinar jugadoras a mostrar y ordenarlas
        all_players = per_player_day["identificacion"].astype(str).unique().tolist()
        if 'jug_sel' in locals() and jug_sel:
            players = [p for p in all_players if p in jug_sel]
        else:
            players = sorted(all_players)

        # Cálculo de UA total por jugadora para ordenar si corresponde
        ua_totals = per_player_day.groupby("identificacion", as_index=False)["ua"].sum().rename(columns={"ua": "ua_total"})
        # Construir dataframe de orden
        order_df = pd.DataFrame({"identificacion": players})
        order_df = order_df.merge(ua_totals, on="identificacion", how="left")
        order_df["ua_total"] = pd.to_numeric(order_df["ua_total"], errors="coerce").fillna(0)
        if sort_key == "UA total":
            ascending = (sort_order == "Ascendente")
            order_df = order_df.sort_values(["ua_total", "identificacion"], ascending=[ascending, True])
        else:  # Nombre
            ascending = (sort_order == "Ascendente")
            order_df = order_df.sort_values(["identificacion"], ascending=[ascending])
        selected_players = order_df["identificacion"].tolist()

        # Convertir fecha a datetime para ejes ordenados en Altair
        per_player_day = per_player_day.copy()
        team_daily = team_daily.copy()
        per_player_day["fecha_dia_dt"] = pd.to_datetime(per_player_day["fecha_sesion"])  # type: ignore
        team_daily["fecha_dia_dt"] = pd.to_datetime(team_daily["fecha_sesion"])  # type: ignore

        # Dibujar por jugadora
        for player in selected_players:
            st.markdown(f"#### {player}")
            p_df = per_player_day[per_player_day["identificacion"].astype(str) == str(player)]
            if p_df.empty:
                st.info("Sin datos en el rango para esta jugadora.")
                continue
            # Join con promedio del equipo
            plot_df = p_df.merge(team_daily[["fecha_dia_dt", "rpe", "ua"]], on="fecha_dia_dt", how="left")

            # RPE: barras (jugadora) + línea (promedio equipo)
            base_rpe = alt.Chart(plot_df).encode(
                x=alt.X("fecha_dia_dt:T", title="Fecha"),
            )
            bars_rpe = base_rpe.mark_bar(color=BRAND_PRIMARY).encode(
                y=alt.Y("rpe:Q", title="RPE diario (media)"),
                tooltip=[
                    "fecha_dia_dt:T",
                    alt.Tooltip("rpe:Q", format=".2f", title="RPE jugadora"),
                    alt.Tooltip("rpe:Q", title="RPE promedio equipo"),
                    alt.Tooltip("pt:Q", title="MD") if "pt" in plot_df.columns else alt.Tooltip("rpe:Q", title="")
                ],
            )

            line_rpe = base_rpe.mark_line(color=BRAND_TEXT, point=True).encode(
                y=alt.Y("rpe:Q", title="RPE promedio equipo"),
            )
            if chart_type == "RPE":
                chart_rpe = alt.layer(bars_rpe, line_rpe).resolve_scale(y='independent').properties(height=220, width="container")
                st.altair_chart(chart_rpe)

            # UA: barras (jugadora) + línea (promedio equipo)
            base_ua = alt.Chart(plot_df).encode(
                x=alt.X("fecha_dia_dt:T", title="Fecha"),
            )
            bars_ua = base_ua.mark_bar(color=BRAND_PRIMARY).encode(
                y=alt.Y("ua:Q", title="UA diario (suma)"),
                tooltip=[
                    "fecha_dia_dt:T",
                    alt.Tooltip("ua:Q", format=".0f", title="UA jugadora"),
                    alt.Tooltip("ua:Q", format=".0f", title="UA promedio equipo"),
                    alt.Tooltip("pt:Q", title="MD") if "pt" in plot_df.columns else alt.Tooltip("ua:Q", title="")
                ],
            )

            line_ua = base_ua.mark_line(color=BRAND_TEXT, point=True).encode(
                y=alt.Y("ua:Q", title="UA promedio equipo"),
            )
            if chart_type == "UA":
                chart_ua = alt.layer(bars_ua, line_ua).resolve_scale(y='independent').properties(height=220, width="container")
                st.altair_chart(chart_ua)

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
                            return ""

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
                    pts = base_acwr.mark_circle(size=60).encode(
                        color=alt.Color("zona:N", scale=alt.Scale(domain=["Sweet Spot", "Baja", "Elevada", "Danger Zone"], range=["#2ca25f", "#9ecae1", "#fdae6b", "#d62728"]), title="Zona"),
                        tooltip=[
                            "fecha_dia_dt:T",
                            alt.Tooltip("acwr:Q", format=".2f"),
                            (alt.Tooltip("pt:Q", title="MD") if "pt" in acwr_src.columns else alt.Tooltip("acwr:Q", title=""))
                        ]
                    )

                    line = base_acwr.mark_line(color=BRAND_TEXT)

                    # Para que los rectángulos cubran todo el eje X, damos una escala X con domain igual al de los datos
                    x_domain = {
                        "values": acwr_src["fecha_dia_dt"].sort_values().astype("datetime64[ns]").tolist()
                    }
                    bg_green = bg_green.encode(y="y0:Q", y2="y1:Q").properties()
                    bg_red = bg_red.encode(y="y0:Q", y2="y1:Q").properties()

                    chart_acwr = alt.layer(bg_green, bg_red, rules, line, pts).resolve_scale(y="shared").properties(height=220, width="container")
                    st.altair_chart(chart_acwr)
            except Exception:
                pass
    except Exception:
        # Evitar que un problema con las gráficas rompa toda la vista
        st.info("No se pudieron renderizar las gráficas por jugadora.")


def checkin_view(df: pd.DataFrame) -> None:
    
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
                sorted(d["identificacion"].dropna().astype(str).unique().tolist())
                if "identificacion" in d.columns
                else []
            )
            jug_sel = st.multiselect("Jugadora(s)", options=jugadores, default=[], placeholder="Selecciona una o mas")
        with f3:
            turnos = ["Turno 1", "Turno 2", "Turno 3"]
            if "turno" in d.columns:
                present = d["turno"].dropna().astype(str).unique().tolist()
                turnos = [t for t in turnos if t in present] or ["Turno 1", "Turno 2", "Turno 3"]
            turno_sel = st.multiselect("Turno(s)", options=turnos, default=[], placeholder="Selecciona uno o mas")
        with f4:
            ics_sel = st.multiselect("ICS", options=["ROJO", "AMARILLO", "VERDE"], default=[], placeholder="Selecciona uno o mas")

    day_mask = d["fecha"].dt.date == sel_date
    day_df = d[day_mask].copy()
    if 'jug_sel' in locals() and jug_sel:
        day_df = day_df[day_df["identificacion"].astype(str).isin(jug_sel)]
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

    add_if("identificacion")
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
    day_df = day_df.merge(d[["fecha_hora", "identificacion", "ICS"]], on=["fecha_hora", "identificacion"], how="left") if "identificacion" in day_df.columns else day_df
    view = day_df[cols + (["ICS"] if "ICS" in day_df.columns else [])].copy()

    # Apply ICS filter if selected
    if 'ics_sel' in locals() and ics_sel and "ICS" in view.columns:
        view = view[view["ICS"].isin(ics_sel)]

    if view.empty:
        st.info("No hay registros que coincidan con los filtros.")
        return
    view = view.rename(columns={
        "identificacion": "Jugadora",
        "fecha_hora": "Fecha",
        "periodizacion_tactica": "Matchday",
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
            st.metric("Rojo", value=c_rojo, border=True)
        with mc2:
            st.metric("Amarillo", value=c_amarillo, border=True)
        with mc3:
            st.metric("Verde", value=c_verde, border=True)

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
        st.dataframe(styler)
    else:
        st.dataframe(view)

    # --- Gráfica por jugadora (día seleccionado) con línea de promedio del equipo ---
    st.divider()
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
        if metric_opt not in plot_src.columns or "identificacion" not in plot_src.columns:
            st.info("No hay datos suficientes para graficar.")
            return
        # Mantener PT si existe
        cols_use = ["identificacion", metric_opt] + (["periodizacion_tactica"] if "periodizacion_tactica" in plot_src.columns else [])
        plot_src = plot_src[cols_use].dropna(subset=[metric_opt])
        plot_src[metric_opt] = pd.to_numeric(plot_src[metric_opt], errors="coerce")
        plot_src = plot_src.dropna(subset=[metric_opt])
        if plot_src.empty:
            st.info("No hay valores para la métrica seleccionada.")
            return
        # Agregar por jugadora por si hubiese múltiples registros; tomar media por jugadora el día
        g = plot_src.groupby("identificacion", as_index=False)[metric_opt].mean().rename(columns={metric_opt: "valor"})
        if "periodizacion_tactica" in plot_src.columns:
            pt_per_player = plot_src.groupby("identificacion", as_index=False)["periodizacion_tactica"].mean().rename(columns={"periodizacion_tactica": "pt"})
            g = g.merge(pt_per_player, on="identificacion", how="left")
        # Orden
        ascending = (sort_order == "Ascendente")
        if sort_key == "Valor":
            g = g.sort_values(["valor", "identificacion"], ascending=[ascending, True])
        else:
            g = g.sort_values(["identificacion"], ascending=[ascending])
        team_avg = float(g["valor"].mean()) if not g.empty else None

        # Altair chart: barras por jugadora + línea horizontal promedio equipo
        chart = alt.Chart(g).encode(
            x=alt.X("nombre_jugadora:N", title="Jugadora", sort=g["identificacion"].tolist()),
            y=alt.Y("valor:Q", title=f"{metric_opt.capitalize()} (1-5)"),
            tooltip=[
                "nombre_jugadora:N",
                alt.Tooltip("valor:Q", format=".2f", title="Valor"),
                (alt.Tooltip("pt:Q", title="PT") if "pt" in g.columns else alt.Tooltip("valor:Q", title="")),
            ],
        )
        bars = chart.mark_bar(color=BRAND_PRIMARY)
        if team_avg is not None:
            rule = alt.Chart(pd.DataFrame({"y": [team_avg]})).mark_rule(color=BRAND_TEXT).encode(y="y:Q")
            st.altair_chart(bars + rule)
        else:
            st.altair_chart(bars)
    except Exception:
        st.info("No se pudo renderizar la gráfica por jugadora.")

    # Downloads
    st.divider()
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
    st.divider()
    st.subheader("Jugadoras que no respondieron")
    jug_df, jug_err = load_jugadoras()
    if jug_err or jug_df is None or jug_df.empty:
        st.info("No se pudo cargar el listado de jugadoras (data/jugadoras.xlsx).")
    else:
        roster = jug_df["identificacion"].astype(str).tolist()
        if 'jug_sel' in locals() and jug_sel:
            roster = [j for j in roster if j in jug_sel]
        responded = set(view["Jugadora"].astype(str).unique().tolist()) if "Jugadora" in view.columns else set()
        missing = [j for j in roster if j not in responded]
        if missing:
            st.dataframe(pd.DataFrame({"Jugadora": missing}).sort_values("Jugadora"))
        else:
            st.success("Todas las jugadoras seleccionadas respondieron en la fecha.")


# def individual_report_view(df: pd.DataFrame) -> None:
    
#     if df is None or df.empty:
#         st.info("No hay registros aún.")
#         return
#     d = df.copy()
#     # Asegurar columnas de fecha
#     if "fecha" not in d.columns and "fecha_hora" in d.columns:
#         d["fecha"] = pd.to_datetime(d["fecha_hora"], errors="coerce")
#     if "fecha_sesion" not in d.columns and "fecha" in d.columns:
#         d["fecha_sesion"] = d["fecha"].dt.date

#     jugadores = (
#         sorted(d["identificacion"].dropna().astype(str).unique().tolist())
#         if "identificacion" in d.columns
#         else []
#     )
#     if not jugadores:
#         st.info("No hay jugadoras en los registros.")
#         return

#     c1, c2 = st.columns([1, 1])
#     with c1:
#         player = st.selectbox("Jugadora", options=jugadores, index=0)
#     with c2:
#         # Rango de fechas predeterminado al rango completo de la jugadora
#         d_player = d[d["identificacion"].astype(str) == str(player)]
#         if "fecha_sesion" in d_player.columns and not d_player["fecha_sesion"].isna().all():
#             min_date = d_player["fecha_sesion"].min()
#             max_date = d_player["fecha_sesion"].max()
#             start, end = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)
#         else:
#             start = end = None

#     # Filtrar por jugadora y rango
#     d = d_player.copy()
#     if start and end and "fecha_sesion" in d.columns:
#         mask = (d["fecha_sesion"] >= start) & (d["fecha_sesion"] <= end)
#         d = d[mask]

#     if d.empty:
#         st.info("No hay registros para los filtros seleccionados.")
#         return

#     st.subheader("Resumen")
#     # Check-in: medias por métrica 1..5
#     checkin_fields = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
#     means = {k: float(pd.to_numeric(d[k], errors="coerce").mean()) if k in d.columns else None for k in checkin_fields}
#     m_cols = st.columns(5)
#     with m_cols[0]:
#         st.metric("Recuperación media", f"{means.get('recuperacion', 0):.2f}" if means.get('recuperacion') is not None else "-")
#     with m_cols[1]:
#         st.metric("Fatiga media", f"{means.get('fatiga', 0):.2f}" if means.get('fatiga') is not None else "-")
#     with m_cols[2]:
#         st.metric("Sueño medio", f"{means.get('sueno', 0):.2f}" if means.get('sueno') is not None else "-")
#     with m_cols[3]:
#         st.metric("Estrés medio", f"{means.get('stress', 0):.2f}" if means.get('stress') is not None else "-")
#     with m_cols[4]:
#         st.metric("Dolor medio", f"{means.get('dolor', 0):.2f}" if means.get('dolor') is not None else "-")

#     # Check-out: totales / medias
#     #m_cols = st.columns(3)
#     with m_cols[0]:
#         ua_total = float(pd.to_numeric(d.get("ua"), errors="coerce").sum()) if "ua" in d.columns else None
#         st.metric("UA total", f"{ua_total:.0f}" if ua_total is not None else "-")
#     with m_cols[1]:
#         min_total = float(pd.to_numeric(d.get("minutos_sesion"), errors="coerce").sum()) if "minutos_sesion" in d.columns else None
#         st.metric("Minutos totales", f"{min_total:.0f}" if min_total is not None else "-")
#     with m_cols[2]:
#         rpe_media = float(pd.to_numeric(d.get("rpe"), errors="coerce").mean()) if "rpe" in d.columns else None
#         st.metric("RPE medio", f"{rpe_media:.2f}" if rpe_media is not None else "-")

#     # Gráficas (mejoradas)
#     st.divider()
#     st.subheader("Gráficas")
#     t = d.copy()
#     if "fecha" in t.columns:
#         t = t.sort_values("fecha")
#     # Series para UA y RPE (con etiqueta de fecha + PT)
#     ua_series = pd.DataFrame(columns=["fecha", "ua"])  # fallback
#     if "ua" in t.columns and "fecha" in t.columns:
#         ua_series = t[["fecha", "ua", "periodizacion_tactica"]].copy() if "periodizacion_tactica" in t.columns else t[["fecha", "ua"]].copy()
#         ua_series["ua"] = pd.to_numeric(ua_series["ua"], errors="coerce")
#         ua_series = ua_series.dropna()
#         ua_series = ua_series.sort_values("fecha")
#         # Etiqueta x: YYYY-MM-DD (PT +n) si existe
#         def _fmt_pt(fecha, pt):
#             try:
#                 d = pd.to_datetime(fecha).date()
#             except Exception:
#                 return str(fecha)
#             if pd.notna(pt):
#                 try:
#                     pt_i = int(pt)
#                     return f"{d} (PT {pt_i:+d})"
#                 except Exception:
#                     pass
#             return f"{d}"
#         if "periodizacion_tactica" in ua_series.columns:
#             ua_series["fecha_pt"] = ua_series.apply(lambda r: _fmt_pt(r["fecha"], r["periodizacion_tactica"]).replace("PT", "MD"), axis=1)
#         else:
#             ua_series["fecha_pt"] = ua_series["fecha"].apply(lambda f: f"{pd.to_datetime(f).date()}" if pd.notna(f) else str(f))
#         ua_series["order"] = range(1, len(ua_series) + 1)
#         try:
#             ua_series["ua_media7"] = ua_series["ua"].rolling(7, min_periods=2).mean()
#         except Exception:
#             ua_series["ua_media7"] = pd.NA
#     rpe_series = pd.DataFrame(columns=["fecha", "rpe"])  # fallback
#     if "rpe" in t.columns and "fecha" in t.columns:
#         rpe_series = t[["fecha", "rpe", "periodizacion_tactica"]].copy() if "periodizacion_tactica" in t.columns else t[["fecha", "rpe"]].copy()
#         rpe_series["rpe"] = pd.to_numeric(rpe_series["rpe"], errors="coerce")
#         rpe_series = rpe_series.dropna().sort_values("fecha")
#         if "periodizacion_tactica" in rpe_series.columns:
#             rpe_series["fecha_pt"] = rpe_series.apply(lambda r: _fmt_pt(r["fecha"], r["periodizacion_tactica"]).replace("PT", "MD"), axis=1)
#         else:
#             rpe_series["fecha_pt"] = rpe_series["fecha"].apply(lambda f: f"{pd.to_datetime(f).date()}" if pd.notna(f) else str(f))
#         rpe_series["order"] = range(1, len(rpe_series) + 1)
#         try:
#             rpe_series["rpe_media7"] = rpe_series["rpe"].rolling(7, min_periods=2).mean()
#         except Exception:
#             rpe_series["rpe_media7"] = pd.NA

#     # Wellness multiserie (1-5): recuperacion, fatiga, sueno, stress, dolor
#     ci_metrics = [m for m in ["recuperacion", "fatiga", "sueno", "stress", "dolor"] if m in t.columns]
#     ci_long = pd.DataFrame(columns=["fecha", "metric", "valor"])  # fallback
#     if ci_metrics and "fecha" in t.columns:
#         use_cols = ["fecha"] + ci_metrics + (["periodizacion_tactica"] if "periodizacion_tactica" in t.columns else [])
#         ci_src = t[use_cols].copy()
#         for m in ci_metrics:
#             ci_src[m] = pd.to_numeric(ci_src[m], errors="coerce")
#         ci_long = ci_src.melt(id_vars=[c for c in ["fecha", "periodizacion_tactica"] if c in ci_src.columns], value_vars=ci_metrics, var_name="metric", value_name="valor").dropna()
#         ci_long = ci_long.sort_values("fecha")
#         # Etiqueta x con PT
#         if "periodizacion_tactica" in ci_long.columns:
#             ci_long["fecha_pt"] = ci_long.apply(lambda r: _fmt_pt(r["fecha"], r["periodizacion_tactica"]).replace("PT", "MD"), axis=1)
#         else:
#             ci_long["fecha_pt"] = ci_long["fecha"].apply(lambda f: f"{pd.to_datetime(f).date()}" if pd.notna(f) else str(f))
#         # order por fecha
#         ci_long = ci_long.merge(ci_long[["fecha", "fecha_pt"]].drop_duplicates().reset_index(drop=True).reset_index().rename(columns={"index": "order"}), on=["fecha", "fecha_pt"], how="left")

#     # Renderizar
#     c1, c2 = st.columns(2)
#     with c1:
#         if not ua_series.empty:
#             base = alt.Chart(ua_series).encode(x=alt.X("fecha_pt:N", sort=alt.SortField("order"), title="Fecha (MD)"))
#             bars = base.mark_bar(color=BRAND_PRIMARY).encode(y=alt.Y("ua:Q", title="UA"), tooltip=["fecha_pt:N", alt.Tooltip("ua:Q", format=".0f", title="UA"), alt.Tooltip("ua_media7:Q", format=".0f", title="Media 7d")])
#             line = base.mark_line(color=BRAND_TEXT).encode(y=alt.Y("ua_media7:Q", title="Media 7d"))
#             ua_chart = alt.layer(bars, line).properties(height=220, title="UA por sesión (con media 7d)")
#             st.altair_chart(ua_chart)
#             with st.expander("Exportar PNG (UA)", expanded=False):
#                 _exportable_chart(ua_chart, key=f"ind_ua_{player}", height=220)
#         else:
#             st.info("Sin datos de UA para graficar.")
#     with c2:
#         if not rpe_series.empty:
#             base = alt.Chart(rpe_series).encode(x=alt.X("fecha_pt:N", sort=alt.SortField("order"), title="Fecha (MD)"))
#             line1 = base.mark_line(color=BRAND_PRIMARY).encode(y=alt.Y("rpe:Q", title="RPE"), tooltip=["fecha_pt:N", alt.Tooltip("rpe:Q", format=".2f", title="RPE"), alt.Tooltip("rpe_media7:Q", format=".2f", title="Media 7d")])
#             line2 = base.mark_line(color=BRAND_TEXT).encode(y=alt.Y("rpe_media7:Q", title="Media 7d"))
#             rpe_chart = alt.layer(line1, line2).properties(height=220, title="RPE por sesión (con media 7d)")
#             st.altair_chart(rpe_chart)
#             with st.expander("Exportar PNG (RPE)", expanded=False):
#                 _exportable_chart(rpe_chart, key=f"ind_rpe_{player}", height=220)
#         else:
#             st.info("Sin datos de RPE para graficar.")

#     st.markdown("-")
#     if not ci_long.empty:
#         ci_chart = alt.Chart(ci_long).mark_line(point=True).encode(
#             x=alt.X("fecha_pt:N", sort=alt.SortField("order"), title="Fecha (MD)"),
#             y=alt.Y("valor:Q", title="Wellness (1-5)", scale=alt.Scale(domain=[1, 5])),
#             color=alt.Color("metric:N", title="Métrica", legend=alt.Legend(orient="bottom")),
#             tooltip=["fecha_pt:N", "metric:N", alt.Tooltip("valor:Q", format=".2f")],
#         ).properties(height=260, title="Wellness (recuperación, fatiga, sueño, estrés, dolor)")
#         st.altair_chart(ci_chart)
#         with st.expander("Exportar PNG (Wellness)", expanded=False):
#             _exportable_chart(ci_chart, key=f"ind_ci_{player}", height=260)
#     else:
#         st.info("Sin datos de Check-in suficientes para graficar.")

#     # Construir HTML para exportación (PDF/HTML)
#     st.divider()
#     st.subheader("Exportar reporte")
#     try:
#         html_bytes = _build_individual_report_html(
#             player=player,
#             start=start,
#             end=end,
#             kpis={
#                 "ua_total": ua_total,
#                 "min_total": min_total,
#                 "rpe_media": rpe_media,
#             },
#             ua_series=ua_series,
#             rpe_series=rpe_series,
#             ci_long=ci_long,
#             detail_df=None,  # omitimos detalle para mantener tamaño bajo; ya hay CSV/JSONL aparte
#         )
#         st.download_button(
#             "Descargar reporte (HTML imprimible a PDF)",
#             data=html_bytes,
#             file_name=f"reporte_individual_{player}.html",
#             mime="text/html",
#             help="Abre el archivo y usa Imprimir -> Guardar como PDF para generar el PDF.",
#         )
#     except Exception:
#         st.info("No se pudo generar el HTML del reporte para exportación.")

#     # Detalle por fecha (tabla)
#     st.divider()
#     st.subheader("Detalle por fecha")
#     t = d.copy()
#     if "fecha" in t.columns:
#         t = t.sort_values("fecha")
#     # Calcular ICS por fila para mostrar en el detalle
#     def _val_cat(v: float) -> str:
#         try:
#             v = float(v)
#         except Exception:
#             return ""
#         if v in (1, 2):
#             return "VERDE"
#         if v == 3:
#             return "AMARILLO"
#         if v in (4, 5):
#             return "ROJO"
#         return ""

#     def _compute_ics(row: pd.Series) -> str:
#         keys = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
#         if not all(k in row and pd.notna(row[k]) for k in keys):
#             return ""
#         cats = {k: _val_cat(row[k]) for k in keys}
#         greens = sum(1 for c in cats.values() if c == "VERDE")
#         yellows = [k for k, c in cats.items() if c == "AMARILLO"]
#         reds = sum(1 for c in cats.values() if c == "ROJO")
#         if reds >= 1:
#             return "ROJO"
#         if len(yellows) >= 3:
#             return "ROJO"
#         if len(yellows) == 2 and ("dolor" in yellows):
#             return "ROJO"
#         if greens == 5:
#             return "VERDE"
#         if greens == 4 and len(yellows) == 1 and ("dolor" not in yellows):
#             return "VERDE"
#         if len(yellows) == 1:
#             return "AMARILLO"
#         if len(yellows) == 2 and ("dolor" not in yellows):
#             return "AMARILLO"
#         return "AMARILLO" if len(yellows) > 0 else ""

#     for col in ["recuperacion", "fatiga", "sueno", "stress", "dolor", "ua", "rpe", "minutos_sesion"]:
#         if col in t.columns:
#             t[col] = pd.to_numeric(t[col], errors="coerce")
#     t["ICS"] = t.apply(_compute_ics, axis=1)

#     cols = []
#     def add_if(col):
#         if col in t.columns:
#             cols.append(col)

#     add_if("fecha")
#     add_if("turno")
#     add_if("periodizacion_tactica")
#     add_if("recuperacion")
#     add_if("fatiga")
#     add_if("sueno")
#     add_if("stress")
#     add_if("dolor")
#     add_if("partes_cuerpo_dolor")
#     add_if("ua")
#     add_if("rpe")
#     add_if("minutos_sesion")
#     add_if("observacion")
#     add_if("ICS")

#     view = t[cols].copy()

#     # Formateos ligeros
#     if "fecha" in view.columns:
#         try:
#             view["fecha"] = pd.to_datetime(view["fecha"]).dt.strftime("%Y-%m-%d")
#         except Exception:
#             pass
#     if "partes_cuerpo_dolor" in view.columns:
#         view["partes_cuerpo_dolor"] = view["partes_cuerpo_dolor"].apply(lambda x: "; ".join(map(str, x)) if isinstance(x, (list, tuple)) else ("" if x is None else str(x)))

#     # Mostrar tabla
#     st.dataframe(view)

#     # Descargas
#     st.divider()

#     c1, c2 = st.columns(2)
#     with c1:
#         csv_bytes = view.to_csv(index=False).encode("utf-8")
#         st.download_button("Descargar CSV (detalle)", data=csv_bytes, file_name=f"reporte_individual_{player}.csv", mime="text/csv")
#     with c2:
#         import json
#         records = view.where(pd.notnull(view), None).to_dict(orient="records")
#         jsonl_str = "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records)
#         st.download_button("Descargar JSONL (detalle)", data=jsonl_str.encode("utf-8"), file_name=f"reporte_individual_{player}.jsonl", mime="application/json")

def risk_view(df: pd.DataFrame, jugadora, turno, start, end) -> None:
    
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return
    d = df.copy()

    #start = pd.Timestamp(start)
    #end = pd.Timestamp(end)
        
    st.divider()
    w_rpe = st.slider("Peso RPE/ACWR", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
    w_well = 1.0 - w_rpe
    st.caption(f"Peso Wellness: {w_well:.2f}")

    # Filtros globales por fecha/turno (pero mantenemos jugadores para todos por defecto)
    if start and end and "fecha_sesion" in d.columns:
        mask = (d["fecha_sesion"] >= start) & (d["fecha_sesion"] <= end)
        d = d[mask]
    if 'turno_sel' in locals() and turno_sel:
        d = d[d["turno"].astype(str).isin(turno_sel)]
    if d.empty:
        st.info("No hay datos en el rango/criterios seleccionados.")
        return

    # Preparar UA por jugadora por día para ACWR
    dd = d.copy()
    if "tipo" in dd.columns:
        dd = dd[dd["tipo"] == "checkOut"]
    if "ua" in dd.columns:
        dd["ua"] = pd.to_numeric(dd["ua"], errors="coerce")
    else:
        dd["ua"] = pd.NA
    dd = dd.dropna(subset=["fecha_sesion"]) if "fecha_sesion" in dd.columns else dd

    # Agrupar UA por jugadora y día
    if dd.empty or "identificacion" not in dd.columns or "fecha_sesion" not in dd.columns:
        acwr_per_player = pd.DataFrame(columns=["identificacion", "acwr"])
    else:
        per_day = (
            dd.groupby(["identificacion", "fecha_sesion"], as_index=False)["ua"].sum()
            .rename(columns={"ua": "ua_total"})
        )
        # Último día de referencia dentro del rango
        end_day = per_day["fecha_sesion"].max() if not per_day.empty else None
        # Rolling para cada jugadora
        def compute_acwr_player(g: pd.DataFrame) -> float | None:
            g = g.sort_values("fecha_sesion").copy()
            g["acute_mean7"] = g["ua_total"].rolling(7, min_periods=3).mean()
            g["chronic_mean28"] = g["ua_total"].rolling(28, min_periods=7).mean()
            g["acwr"] = g["acute_mean7"] / g["chronic_mean28"]
            # tomar valor del último día del grupo que coincida con end_day
            last = g[g["fecha_sesion"] == end_day]
            if not last.empty and pd.notna(last["acwr"].iloc[0]):
                return float(last["acwr"].iloc[0])
            # fallback: último acwr disponible
            last_non_na = g.dropna(subset=["acwr"]).tail(1)
            return float(last_non_na["acwr"].iloc[0]) if not last_non_na.empty else None

        acwr_vals = (
            per_day.groupby("identificacion")
            .apply(compute_acwr_player)
            #.reset_index(name="acwr")
        )
        acwr_per_player = acwr_vals

        if acwr_per_player.empty:
            st.info("No hay jugadoras para mostrar.")
            return

        #st.dataframe(acwr_vals)

    # Mapear ACWR a riesgo 0..1 (proximidad a lesión)
    def acwr_to_risk(x: float | None) -> float:
        if x is None or pd.isna(x):
            return 0.5  # desconocido -> riesgo medio
        try:
            x = float(x)
        except Exception:
            return 0.5
        # piecewise: <0.8 bajo; 0.8-1.3 sweet; 1.3-1.5 elevado; >1.5 peligro
        if x < 0.8:
            return 0.2
        if 0.8 <= x < 1.3:
            # de 0.8 a 1.3 sube de 0.3 a 0.5 suavemente
            return 0.3 + (x - 0.8) * (0.2 / 0.5)
        if 1.3 <= x < 1.5:
            # de 1.3 a 1.5 sube de 0.6 a 0.8
            return 0.6 + (x - 1.3) * (0.2 / 0.2)
        # >= 1.5
        return 1.0

    # Wellness: calcular ICS más reciente por jugadora en rango
    ci = d.copy()
    # Mantener filas que tengan al menos uno de los campos de check-in
    checkin_fields = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
    existing_fields = [c for c in checkin_fields if c in ci.columns]
    if existing_fields:
        ci = ci[ci[existing_fields].notna().any(axis=1)]
    else:
        ci = pd.DataFrame(columns=d.columns)

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
        if not all(k in row and pd.notna(row[k]) for k in keys):
            return ""
        cats = {k: _val_cat(row[k]) for k in keys}
        greens = sum(1 for c in cats.values() if c == "VERDE")
        yellows = [k for k, c in cats.items() if c == "AMARILLO"]
        reds = sum(1 for c in cats.values() if c == "ROJO")
        if reds >= 1:
            return "ROJO"
        if len(yellows) >= 3:
            return "ROJO"
        if len(yellows) == 2 and ("dolor" in yellows):
            return "ROJO"
        if greens == 5:
            return "VERDE"
        if greens == 4 and len(yellows) == 1 and ("dolor" not in yellows):
            return "VERDE"
        if len(yellows) == 1:
            return "AMARILLO"
        if len(yellows) == 2 and ("dolor" not in yellows):
            return "AMARILLO"
        return "AMARILLO" if len(yellows) > 0 else ""

    if not ci.empty:
        ci = ci.copy()
        for k in checkin_fields:
            if k in ci.columns:
                ci[k] = pd.to_numeric(ci[k], errors="coerce")
        ci["ICS"] = ci.apply(_compute_ics, axis=1)
        # último ICS por jugadora
        ci = ci.sort_values("fecha") if "fecha" in ci.columns else ci
        last_ics = ci.dropna(subset=["ICS"]) if "ICS" in ci.columns else pd.DataFrame()
        if not last_ics.empty and "identificacion" in last_ics.columns:
            last_idx = last_ics.groupby("identificacion")["fecha"].idxmax() if "fecha" in last_ics.columns else last_ics.groupby("identificacion").tail(1).index
            last_ics = last_ics.loc[last_idx, ["identificacion", "ICS"]]
        else:
            last_ics = pd.DataFrame(columns=["identificacion", "ICS"])
    else:
        last_ics = pd.DataFrame(columns=["identificacion", "ICS"])

    def ics_to_risk(cat: str) -> float:
        if cat == "ROJO":
            return 1.0
        if cat == "AMARILLO":
            return 0.6
        if cat == "VERDE":
            return 0.2
        return 0.5

    # Merge ACWR y ICS
    players = sorted(set(d.get("identificacion", pd.Series(dtype=str)).dropna().astype(str).tolist()))
    
    if 'jug_sel' in locals() and jug_sel:
        players = [p for p in players if p in jug_sel]
    risk_df = pd.DataFrame({"identificacion": players})

 
    risk_df = risk_df.merge(acwr_per_player, on="identificacion", how="left")
    risk_df = risk_df.merge(last_ics, on="identificacion", how="left")
    risk_df["risk_acwr"] = risk_df["acwr"].apply(acwr_to_risk)
    risk_df["risk_ics"] = risk_df["ICS"].apply(ics_to_risk)
    risk_df["riesgo"] = (w_rpe * risk_df["risk_acwr"]) + ((1.0 - w_rpe) * risk_df["risk_ics"]) if "risk_acwr" in risk_df.columns else risk_df["risk_ics"]

    if risk_df.empty:
        st.info("No hay jugadoras para mostrar.")
        return

    # Mostrar KPIs y tabla
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Jugadoras", value=len(risk_df), border=True)
    with k2:
        st.metric("Riesgo medio", value=f"{risk_df['riesgo'].mean():.2f}", border=True)
    with k3:
        st.metric(
            "% en zona de peligro (ACWR>1.5)",
            value=f"{(risk_df['acwr'] > 1.5).fillna(False).mean() * 100:.0f}%" if 'acwr' in risk_df.columns else "-",
            border=True
        )

    # Ordenar por riesgo
    risk_df = risk_df.sort_values(["riesgo", "identificacion"], ascending=[False, True])

    # Gráfico de barras
    plot = risk_df.copy()
    plot["riesgo_pct"] = (plot["riesgo"].clip(0, 1) * 100.0).round(1)
    chart = alt.Chart(plot).encode(
        x=alt.X("riesgo_pct:Q", title="Proximidad al riesgo (%)", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("nombre_jugadora:N", sort=plot["identificacion"].tolist(), title="Jugadora"),
        color=alt.Color("riesgo_pct:Q", scale=alt.Scale(scheme="reds"), legend=None),
        tooltip=[
            "nombre_jugadora:N",
            alt.Tooltip("riesgo_pct:Q", title="Riesgo %", format=".1f"),
            alt.Tooltip("acwr:Q", title="ACWR", format=".2f"),
            alt.Tooltip("ICS:N", title="ICS"),
        ],
    ).mark_bar()
    st.altair_chart(chart.properties(height=max(200, 24 * len(plot))))

    # Tabla detallada
    st.divider()
    show_tbl = plot[["identificacion", "acwr", "risk_acwr", "ICS", "risk_ics", "riesgo", "riesgo_pct"]].copy()
    show_tbl = show_tbl.rename(columns={
        "identificacion": "Jugadora",
        "acwr": "ACWR",
        "risk_acwr": "Riesgo ACWR (0-1)",
        "ICS": "ICS",
        "risk_ics": "Riesgo Wellness (0-1)",
        "riesgo": "Riesgo combinado (0-1)",
        "riesgo_pct": "Riesgo %",
    })
    st.dataframe(show_tbl)

def home_view(df: pd.DataFrame) -> None:
    """Vista de inicio con KPIs del día anterior y lista de jugadoras en riesgo.
    - RPE promedio (ayer) y UA total (ayer) a partir de Check-out.
    - % en riesgo calculado desde el último Check-in por jugadora.
    - Promedio de índices subjetivos del último Check-in.
    - Lista de jugadoras en riesgo en rojo y negritas.
    """
    #st.subheader("Inicio")
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return

    d = df.copy()
    # Asegurar columna temporal 'fecha'
    if "fecha" not in d.columns and "fecha_hora" in d.columns:
        d["fecha"] = pd.to_datetime(d["fecha_hora"], errors="coerce")

    # KPIs y filtros del día anterior
    from datetime import date, timedelta  # local import to avoid top-level conflicts
    avg_rpe, ua_total = None, None
    team_avg_rpe, team_ua_total = None, None
    selected_player: str | None = None
    d_y = pd.DataFrame()
    if "fecha" in d.columns and not d["fecha"].isna().all():
        yesterday = date.today() - timedelta(days=1)
        d["fecha_hora"] = pd.to_datetime(d["fecha_hora"], errors="coerce")

        d_y = d[d["fecha_hora"].dt.date == yesterday].copy()
        d_y_all = d_y.copy()
        #st.dataframe(d_y_all)
        # KPIs equipo (ayer) sin filtrar
        if not d_y_all.empty:
            if "rpe" in d_y_all.columns:
                try:
                    s_all = d_y_all["rpe"].dropna().astype(float)
                    team_avg_rpe = float(s_all.mean()) if not s_all.empty else None
                except Exception:
                    team_avg_rpe = None
            if "ua" in d_y_all.columns:
                try:
                    s_all = d_y_all["ua"].dropna().astype(float)
                    team_ua_total = float(s_all.sum()) if not s_all.empty else None
                except Exception:
                    team_ua_total = None
        # Filtro por jugadora (solo nombres presentes ayer)
        players = sorted(d_y.get("identificacion", pd.Series([], dtype=str)).dropna().astype(str).unique().tolist())
        sel = st.selectbox("Filtrar jugadora (día anterior)", options=["(Todas)"] + players, index=0)
        selected_player = None if sel == "(Todas)" else sel
        if selected_player:
            d_y = d_y[d_y["identificacion"].astype(str) == selected_player]
        # KPIs del día anterior con filtro aplicado
        if not d_y.empty:
            if "rpe" in d_y.columns:
                try:
                    series = d_y["rpe"].dropna().astype(float)
                    avg_rpe = float(series.mean()) if not series.empty else None
                except Exception:
                    avg_rpe = None
            if "ua" in d_y.columns:
                try:
                    series = d_y["ua"].dropna().astype(float)
                    ua_total = float(series.sum()) if not series.empty else None
                except Exception:
                    ua_total = None

    # Control: Umbral de riesgo persistente
    st.markdown("---")
    if "risk_threshold" not in st.session_state:
        st.session_state["risk_threshold"] = 7.0
    threshold = st.slider(
        "Umbral de riesgo (0-10)",
        min_value=0.0,
        max_value=10.0,
        value=float(st.session_state["risk_threshold"]),
        step=0.5,
        help="Las jugadoras con riesgo igual o superior a este valor aparecerán como 'en riesgo'.",
        key="risk_threshold",
    )

    # Riesgo por último Check-in (sincronizado con filtro de jugadora si aplica)
    wellness_cols = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
    have_wellness = [c for c in wellness_cols if c in d.columns]
    risk_pct = None
    subj_avgs = {}
    at_risk_rows: list[dict] = []  # guardar detalles para descripción
    # El valor ya queda almacenado por el slider con key; usar la variable local
    threshold = float(threshold)
    if have_wellness and "id_jugadora" in d.columns:
        d_ci = d.dropna(subset=have_wellness, how="any").copy()
        if selected_player:
            d_ci = d_ci[d_ci.get("identificacion", "").astype(str) == selected_player]
        if not d_ci.empty:
            d_ci = d_ci.sort_values("fecha")
            last_ci = d_ci.groupby("id_jugadora", as_index=False).tail(1)

            def _risk_row(r: pd.Series) -> float:
                try:
                    rec = float(r.get("recuperacion", 0) or 0)
                    fat = float(r.get("fatiga", 0) or 0)
                    sue = float(r.get("sueno", 0) or 0)
                    stre = float(r.get("stress", 0) or 0)
                    dol = float(r.get("dolor", 0) or 0)
                except Exception:
                    return 0.0
                raw = (fat + stre + dol) - (rec + sue)  # [-8, +12]
                rescaled = (raw + 8.0) / 20.0 * 10.0  # 0..10
                return float(max(0.0, min(10.0, rescaled)))

            last_ci["riesgo"] = last_ci.apply(_risk_row, axis=1)
            if len(last_ci) > 0:
                risk_pct = 100.0 * (last_ci["riesgo"] >= threshold).mean()
            # Preparar filas de riesgo con detalles (componentes wellness + UA/RPE de ayer)
            name_col = "identificacion" if "identificacion" in last_ci.columns else None
            if name_col:
                risk_subset = last_ci[last_ci["riesgo"] >= threshold].copy()
                # Adjuntar UA/RPE de ayer por jugadora si existen
                if not d_y.empty and "identificacion" in d_y.columns:
                    # Agregar UA y RPE de ayer (sum/mean) por jugadora
                    map_ua = (
                        d_y.groupby("identificacion")["ua"].sum(min_count=1).to_dict() if "ua" in d_y.columns else {}
                    )
                    map_rpe = (
                        d_y.groupby("identificacion")["rpe"].mean().to_dict() if "rpe" in d_y.columns else {}
                    )
                else:
                    map_ua, map_rpe = {}, {}
                for _, row in risk_subset.iterrows():
                    name = str(row.get(name_col, ""))
                    det = {
                        "identificacion": name,
                        "riesgo": float(row.get("riesgo", 0) or 0),
                        "recuperacion": row.get("recuperacion"),
                        "fatiga": row.get("fatiga"),
                        "sueno": row.get("sueno"),
                        "stress": row.get("stress"),
                        "dolor": row.get("dolor"),
                        "ua_ayer": map_ua.get(name),
                        "rpe_ayer": map_rpe.get(name),
                    }
                    at_risk_rows.append(det)
            for c in have_wellness:
                try:
                    subj_avgs[c] = float(last_ci[c].astype(float).mean())
                except Exception:
                    subj_avgs[c] = None

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("RPE promedio (ayer)", value=(f"{avg_rpe:.1f}" if avg_rpe is not None else "-"))
    with k2:
        st.metric("UA total (ayer)", value=(f"{ua_total:.0f}" if ua_total is not None else "-"))
    with k3:
        st.metric("% en riesgo", value=(f"{risk_pct:.0f}%" if risk_pct is not None else "-"))
    with k4:
        try:
            st.metric("Índice subjetivo (media)", value=(f"{pd.Series(subj_avgs).mean():.2f}" if subj_avgs else "-"))
        except Exception:
            st.metric("Índice subjetivo (media)", value="-")

    st.markdown("---")
    st.subheader("Jugadoras en riesgo (día anterior y último CI)")
    if at_risk_rows:
        # Ordenar por mayor riesgo
        at_risk_rows = sorted(at_risk_rows, key=lambda x: x.get("riesgo", 0), reverse=True)
        for det in at_risk_rows:
            name = det.get("identificacion", "-")
            cols = st.columns([1, 8])
            with cols[0]:
                clicked = st.button("Ver informe", key=f"risk_go_{name}")
            with cols[1]:
                # Descripción breve con componentes que sugieren riesgo
                msg = (
                    f"<span style='color:#c62828; font-weight:700'>{name}</span> — "
                    f"Riesgo {det.get('riesgo', 0):.1f}. "
                    f"Wellness: Rec {det.get('recuperacion','-')}, Fat {det.get('fatiga','-')}, Sue {det.get('sueno','-')}, "
                    f"Estr {det.get('stress','-')}, Dol {det.get('dolor','-')}. "
                    f"UA ayer: {('-' if det.get('ua_ayer') is None else det.get('ua_ayer'))}; "
                    f"RPE ayer: {('-' if det.get('rpe_ayer') is None else det.get('rpe_ayer'))}"
                )
                st.markdown(msg, unsafe_allow_html=True)
            if clicked:
                # navegación diferida para evitar conflicto con widgets existentes
                st.session_state["selected_player"] = name
                st.session_state["nav_to_report"] = True
                st.experimental_rerun()
    else:
        st.success("Sin jugadoras en riesgo según el umbral actual.")

def individual_report_view(df: pd.DataFrame, jugadora) -> None:
    """Informe individual de una jugadora con sus registros recientes.
    Muestra últimos registros de Check-in y Check-out, y KPIs simples.
    """
    st.subheader(f"Reporte individual — {jugadora['identificacion']}")
    if df is None or df.empty:
        st.info("No hay registros aún.")
        return

    d = df.copy()
    if "fecha" not in d.columns and "fecha_hora" in d.columns:
        d["fecha"] = pd.to_datetime(d["fecha_hora"], errors="coerce")

    # Filtrar por identificacion
    if "identificacion" not in d.columns:
        st.info("No hay columna 'nombre_jugadora' en los datos.")
        return
    p = d[d["identificacion"].astype(str) == str(jugadora["identificacion"])].copy()
    if p.empty:
        st.info("Sin registros para esta jugadora.")
        return

    # KPIs simples (últimos 7 días)
    try:
        max_date = p["fecha"].max()
        window_start = max_date - pd.Timedelta(days=7)
        p7 = p[(p["fecha"] >= window_start) & (p["fecha"] <= max_date)].copy()
    except Exception:
        p7 = p

    # RPE y UA
    try:
        rpe_avg_7d = float(p7["rpe"].dropna().astype(float).mean()) if "rpe" in p7.columns else None
    except Exception:
        rpe_avg_7d = None
    try:
        ua_sum_7d = float(p7["ua"].dropna().astype(float).sum()) if "ua" in p7.columns else None
    except Exception:
        ua_sum_7d = None

    # Último check-in riesgo
    wellness_cols = ["recuperacion", "fatiga", "sueno", "stress", "dolor"]
    have_wellness = [c for c in wellness_cols if c in p.columns]
    last_risk = None
    if have_wellness and "fecha" in p.columns:
        ci = p.dropna(subset=have_wellness, how="any").sort_values("fecha").tail(1)
        if not ci.empty:
            row = ci.iloc[0]
            try:
                rec = float(row.get("recuperacion", 0) or 0)
                fat = float(row.get("fatiga", 0) or 0)
                sue = float(row.get("sueno", 0) or 0)
                stre = float(row.get("stress", 0) or 0)
                dol = float(row.get("dolor", 0) or 0)
                raw = (fat + stre + dol) - (rec + sue)
                last_risk = float(max(0.0, min(10.0, (raw + 8.0) / 20.0 * 10.0)))
            except Exception:
                last_risk = None

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("RPE medio (7d)", value=(f"{rpe_avg_7d:.1f}" if rpe_avg_7d is not None else "-"))
    with k2:
        st.metric("UA total (7d)", value=(f"{ua_sum_7d:.0f}" if ua_sum_7d is not None else "-"))
    with k3:
        st.metric("Riesgo último CI", value=(f"{last_risk:.1f}" if last_risk is not None else "-"))

    st.markdown("---")
    # Tabla de últimos registros
    if "fecha" in p.columns:
        p = p.sort_values("fecha", ascending=False)
    st.dataframe(p)

def data_filters(modo: int = 1):
    jug_df, jug_error = load_jugadoras_db()    
    comp_df, comp_error = load_competiciones_db()
    
    if modo == 1:
        col1, col2, col3 = st.columns([2,1,2])
    else:
        records = load_lesiones_db() 

        if records.empty:    
            st.warning("No hay datos de lesiones disponibles.")
            st.stop()   
        col1, col2, col3, col4 = st.columns([2,1,2,1])

    with col1:
        competiciones_options = comp_df.to_dict("records")
        competicion = st.selectbox(
            "Plantel",
            options=competiciones_options,
            format_func=lambda x: f'{x["identificacion"]} ({x["codigo"]})',
            placeholder="Seleccione un plantel",
            index=3,
        )
        
    with col2:
        posicion = st.selectbox(
            "Posición",
            options=list(MAP_POSICIONES.values()),
            placeholder="Seleccione una Posición",
            index=None
        )
        
    with col3:
        if competicion:
            codigo_competicion = competicion["codigo"]
            jug_df_filtrado = jug_df[jug_df["plantel"] == codigo_competicion]
        else:
            jug_df_filtrado = jug_df

        if posicion:
            jug_df_filtrado = jug_df_filtrado[jug_df_filtrado["posicion"] == posicion]

        jugadoras_filtradas = jug_df_filtrado.to_dict("records")

        jugadora_seleccionada = st.selectbox(
            "Jugadora",
            options=jugadoras_filtradas,
            format_func=lambda x: f'{jugadoras_filtradas.index(x) + 1} - {x["identificacion"]} {x["apellido"]}',
            placeholder="Seleccione una Jugadora",
            index=None
        )

    if modo >= 2:
        with col4:
            # Filtrado por jugadora seleccionada
            if jugadora_seleccionada:
                records = records[records["id_jugadora"] == jugadora_seleccionada["identificacion"]]
            else:
                if modo == 2:
                    records = pd.DataFrame()
                elif modo == 3:
                    # modo >= 3 → filtrar por todas las jugadoras del plantel o posición
                    if not jug_df_filtrado.empty and "identificacion" in jug_df_filtrado.columns:
                        ids_validos = jug_df_filtrado["identificacion"].astype(str).tolist()
                        records = records[records["id_jugadora"].astype(str).isin(ids_validos)]
                    else:
                        records = pd.DataFrame()

            # Verificar si hay registros
            if records.empty:
                selected_tipo = st.selectbox(
                "Tipo de lesión",
                ["NO APLICA"],
                disabled=True)
            else:
                # Mostrar filtro activo si hay registros
                tipos = sorted(records["tipo_lesion"].dropna().unique())
                selected_tipo = st.selectbox(
                    "Tipo de lesión",
                    ["Todas"] + tipos,
                    disabled=False
                )

                if selected_tipo and selected_tipo != "Todas":
                    records = records[records["tipo_lesion"] == selected_tipo]

   
    #st.dataframe(jug_df_filtrado)
    # Si no hay jugadoras en ese plantel o posición
    if jug_df_filtrado.empty:
        #st.warning("⚠️ No hay jugadoras disponibles para este plantel o posición seleccionada.")
        jugadora_seleccionada = None
        if modo == 1:
            return None, posicion
        else:
            return None, posicion, pd.DataFrame()  # Devuelve vacío

    if modo == 1:
        return jugadora_seleccionada, posicion
    else:
        return jugadora_seleccionada, posicion, records
