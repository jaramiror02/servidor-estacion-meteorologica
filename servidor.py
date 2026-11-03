from pathlib import Path
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify
import requests

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA = Path(__file__).resolve().parent
ARCHIVO_CLAVE = CARPETA / "clave.txt"

STATION_ID = "IOLIVA129"

URL_API_ACTUAL = (
    "https://api.weather.com/v2/pws/observations/current"
)

URL_API_HISTORICO = (
    "https://api.weather.com/v2/pws/observations/hourly/7day"
)


# ==========================================
# LECTURA DE LA CLAVE API
# ==========================================

def leer_clave():
    """Lee la clave API del archivo independiente."""

    if not ARCHIVO_CLAVE.exists():
        raise FileNotFoundError("No se encuentra el archivo clave.txt")

    for linea in ARCHIVO_CLAVE.read_text(
        encoding="utf-8"
    ).splitlines():

        if linea.strip().startswith("WEATHER_API_KEY="):
            return linea.split("=", 1)[1].strip()

    raise ValueError(
        "No se encuentra WEATHER_API_KEY en clave.txt"
    )


# ==========================================
# PÁGINA PRINCIPAL
# ==========================================

@app.route("/")
def inicio():
    return "Servidor de la estación meteorológica en funcionamiento."


# ==========================================
# DATOS METEOROLÓGICOS ACTUALES
# ==========================================

@app.route("/api/estado")
def estado():

    try:
        api_key = leer_clave()

        respuesta = requests.get(
            URL_API_ACTUAL,
            params={
                "stationId": STATION_ID,
                "format": "json",
                "units": "m",
                "numericPrecision": "decimal",
                "apiKey": api_key,
            },
            timeout=15,
        )

        respuesta.raise_for_status()
        datos = respuesta.json()

        observaciones = datos.get("observations", [])

        if not observaciones:
            return jsonify({
                "error": "La API no ha devuelto observaciones."
            }), 502

        obs = observaciones[0]
        metric = obs.get("metric", {})

        resultado = {
            "estacion": STATION_ID,
            "fecha": obs.get("obsTimeLocal"),
            "temperatura_C": metric.get("temp"),
            "humedad_pct": obs.get("humidity"),
            "viento_kmh": metric.get("windSpeed"),
            "rafaga_kmh": metric.get("windGust"),
            "direccion_viento_grados": obs.get("winddir"),
            "lluvia_acumulada_mm": metric.get("precipTotal"),
            "radiacion_solar_W_m2": obs.get("solarRadiation"),
            "indice_uv": obs.get("uv"),
        }

        return jsonify(resultado)

    except FileNotFoundError:
        return jsonify({
            "error": "No se encuentra clave.txt."
        }), 500

    except ValueError as error:
        return jsonify({"error": str(error)}), 500

    except requests.RequestException:
        return jsonify({
            "error": "No se han podido consultar los datos meteorológicos."
        }), 502

    except (KeyError, IndexError, TypeError):
        return jsonify({
            "error": "La respuesta de la API no tiene el formato esperado."
        }), 502


# ==========================================
# DATOS HISTÓRICOS DE LAS ÚLTIMAS 24 HORAS
# ==========================================

@app.route("/api/historico")
def historico():

    try:
        api_key = leer_clave()

        respuesta = requests.get(
            URL_API_HISTORICO,
            params={
                "stationId": STATION_ID,
                "format": "json",
                "units": "m",
                "numericPrecision": "decimal",
                "apiKey": api_key,
            },
            timeout=20,
        )

        # La API puede responder 204 si no hay registros.
        if respuesta.status_code == 204:
            return jsonify({
                "estacion": STATION_ID,
                "registros": [],
                "numero_registros": 0,
                "mensaje": "No hay datos históricos disponibles."
            })

        respuesta.raise_for_status()

        datos = respuesta.json()
        observaciones = datos.get("observations", [])

        # Momento actual y límite de las últimas 24 horas.
        ahora = datetime.now(timezone.utc)
        limite = ahora - timedelta(hours=24)

        registros = []

        for obs in observaciones:

            epoch = obs.get("epoch")

            if epoch is None:
                continue

            fecha_utc = datetime.fromtimestamp(
                float(epoch),
                tz=timezone.utc
            )

            # Solo conservamos las últimas 24 horas.
            if fecha_utc < limite or fecha_utc > ahora:
                continue

            metric = obs.get("metric", {})

            registro = {
                "fecha": obs.get("obsTimeLocal"),
                "epoch": int(epoch),
                "temperatura_C": metric.get("tempAvg"),
                "lluvia_mm": metric.get("precipTotal"),
            }

            registros.append(registro)

        # Orden cronológico.
        registros.sort(key=lambda x: x["epoch"])

        resultado = {
            "estacion": STATION_ID,
            "numero_registros": len(registros),
            "registros": registros,
        }

        return jsonify(resultado)

    except FileNotFoundError:
        return jsonify({
            "error": "No se encuentra clave.txt."
        }), 500

    except ValueError as error:
        return jsonify({"error": str(error)}), 500

    except requests.RequestException:
        return jsonify({
            "error": "No se han podido consultar los datos históricos."
        }), 502

    except (KeyError, IndexError, TypeError, OverflowError):
        return jsonify({
            "error": "La respuesta histórica no tiene el formato esperado."
        }), 502


# ==========================================
# INICIO DEL SERVIDOR
# ==========================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
