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

### Estructura de cada registro (JSONL)

```json
{
  "id_jugadora": "...",
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

## Auth

El sistema de autenticación desarrollado para este proyecto está diseñado para ser seguro, modular y reutilizable entre distintas aplicaciones. Está compuesto por tres capas principales: configuración, lógica base e interfaz de usuario, lo que permite mantener una arquitectura limpia y fácilmente integrable.

Principales características

#### **Autenticación JWT (JSON Web Tokens)**

- Uso de JWT firmados con algoritmo HS256 y un tiempo de expiración configurable (st.secrets["auth"]["time"]).
- Cada token contiene la identidad del usuario, su rol y una fecha de expiración.
- Los tokens se almacenan cifrados y se renuevan automáticamente al volver a iniciar sesión.

#### **Manejo de sesiones seguras con cookies cifradas**

- Implementación con EncryptedCookieManager, usando un secreto distinto al del JWT.
- Cada usuario tiene su propia cookie cifrada, identificada como auth_token_usuario@correo.
- Las sesiones son independientes entre usuarios y navegadores, incluso en Streamlit Cloud gratuito.
- El cierre de sesión (logout()) solo afecta al usuario actual, sin interferir en otras sesiones activas.

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