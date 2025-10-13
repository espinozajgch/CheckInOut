# Wellness & RPE App

Aplicación en Streamlit para registrar Wellness (Check-in) y RPE/UA (Check-out) por jugadora.

## Estructura

```
app.py
src/
  auth.py
  io_files.py
  schema.py
  ui_components.py
data/
  jugadoras.xlsx        # (sube aquí tu archivo con columnas: id_jugadora, nombre_jugadora)
  partes_cuerpo.xlsx    # (sube aquí tu archivo con columna: parte)
  registros.jsonl       # se crea automáticamente (JSON Lines)
requirements.txt
README.md
```

## Requisitos

- Python 3.9+
- pip

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

## Credenciales

- Por defecto: usuario `admin`, contraseña `admin`.
- Puedes configurar variables de entorno en un `.env` (opcional):

```
TRAINER_USER=mi_usuario
TRAINER_PASS=mi_password
```

## Archivos de datos

- Si faltan `data/jugadoras.xlsx` o `data/partes_cuerpo.xlsx`, la app te permitirá descargar plantillas para rellenar.
- Formatos:
  - `jugadoras.xlsx`: columnas `id_jugadora`, `nombre_jugadora`.
  - `partes_cuerpo.xlsx`: columna `parte`.
- Los registros se guardan en `data/registros.jsonl` con una línea JSON por registro.

### Estructura de cada registro (JSONL)

```json
{
  "identificacion": "...",
  "nombre": "...",
  "fecha_hora": "YYYY-MM-DDTHH:MM:SS",
  "tipo": "checkIn|checkOut",
  "turno": "Turno 1|Turno 2|Turno 3",
  "periodizacion_tactica": "-6..+6",
  "recuperacion": int,
  "fatiga": int,
  "sueno": int,
  "stress": int,
  "dolor": int,
  "partes_cuerpo_dolor": [],
  "minutos_sesion": int,
  "rpe": int,
  "ua": int,
  "en_periodo": bool,
  "observacion": "..."
}
```

Clave de actualización (upsert): `(id_jugadora, fecha YYYY-MM-DD, turno)`.
El campo `turno` es obligatorio en el formulario (por defecto: "Turno 1").
Si ya existe un registro para esa combinación, al guardar se actualiza en lugar de crear uno nuevo.

## Validaciones

- Jugadora obligatoria.
- Check-in: escalas 1–5 (recuperación, fatiga, sueño, estrés, dolor). Si dolor > 1, seleccionar al menos una parte del cuerpo.
- Check-out: minutos > 0, RPE 1–10. Se calcula automáticamente UA = RPE × minutos.

## Notas

- Vista de una sola página, previsualización antes de guardar y botón deshabilitado hasta cumplir validaciones.
- Tras guardar, se limpia el formulario (recarga de la app).

## Contributing

- Haz un fork del repositorio.

- Configuración de remoto

```bash
git remote add upstream https://github.com/lucbra21/DuxLesiones.git
git remote -v
```

- Crea una rama nueva para tus cambios
- Realiza tus modificaciones y haz commit
- Haz push a tu fork
- Abre un Pull Request al repositorio original