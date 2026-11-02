from pathlib import Path
from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Carpeta donde se encuentran los archivos del proyecto
CARPETA = Path(__file__).resolve().parent
ARCHIVO_CLAVE = CARPETA / "clave.txt"

STATION_ID = "IOLIVA129"
URL_API = "https://api.weather.com/v2/pws/observations/current"


def leer_clave():
  """Lee la clave API del archivo independiente."""
  if not ARCHIVO_CLAVE.exists():
    raise FileNotFoundError("No se encuentra el archivo clave.txt")

  for linea in ARCHIVO_CLAVE.read_text(encoding="utf-8").splitlines():
    if linea.strip().startswith("WEATHER_API_KEY="):
      return linea.split("=", 1)[1].strip()

  raise ValueError("No se encuentra WEATHER_API_KEY en clave.txt")


@app.route("/")
def inicio():
  return "Servidor de la estación meteorológica en funcionamiento."


@app.route("/api/estado")
def estado():
  try:
    api_key = leer_clave()

    respuesta = requests.get(
        URL_API,
        params={
            "stationId": STATION_ID,
            "format": "json",
            "units": "m",
            "apiKey": api_key,
        },
        timeout=15,
    )

    respuesta.raise_for_status()
    datos = respuesta.json()

    observaciones = datos.get("observations", [])
    if not observaciones:
      return jsonify({"error": "La API no ha devuelto observaciones."}), 502

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
    return jsonify({"error": "No se encuentra clave.txt."}), 500
  except ValueError as error:
    return jsonify({"error": str(error)}), 500
  except requests.RequestException:
    return jsonify(
        {"error": "No se han podido consultar los datos meteorológicos."}
    ), 502
  except (KeyError, IndexError, TypeError, ValueError):
    return jsonify(
        {"error": "La respuesta de la API no tiene el formato esperado."}
    ), 502


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=False)
