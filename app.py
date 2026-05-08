from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import os
import time
from datetime import datetime

# Importamos controladores
from controllers.view_controller import view_bp
from controllers.manual_controller import manual_bp 

# Importamos servicios
from services.weather_api_service import obtener_clima_por_coordenadas, obtener_clima_por_municipio
from services.normalizer_service import normalizar_datos_aemet
from services.geolocation_service import resolve_location, get_city_info
from services.alert_service import get_alert_service
from services.logging_service import log_info, log_error, log_warning
from repositories.json_repository import append            

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_secreta")

# Registro de Blueprints
app.register_blueprint(view_bp)
app.register_blueprint(manual_bp)


@app.route("/api/clima")
def api_clima():
    """
    Gateway inteligente: Resuelve ubicación, obtiene datos y los persiste.
    Fuentes oficiales: IP-API.com para geolocalización, AEMET para clima.
    """
    # 1. Extracción de parámetros
    lat_req = request.args.get('lat')
    lon_req = request.args.get('lon')
    ciudad_req = request.args.get('ciudad')

    # Fallback: Si todo vacío, intentar geolocalización por IP
    if not lat_req and not lon_req and not ciudad_req:
        from services.geolocation_service import get_geolocation_service
        geo = get_geolocation_service()
        ip_loc = geo.get_location_by_ip()
        if ip_loc:
            lat_req = ip_loc.get("lat")
            lon_req = ip_loc.get("lon")

    # 2. Resolución de Ubicación (fuentes oficiales)
    location_data = resolve_location(
        lat=lat_req and float(lat_req),
        lon=lon_req and float(lon_req),
        city=ciudad_req
    )

    # Verificación
    if not location_data.get("success", True) and not location_data.get("lat"):
        log_warning("Fallo en resolución de ubicación. Usando fallback.")
        return jsonify({
            "status": "warning",
            "message": "Ubicación no encontrada, usando datos por defecto.",
            "municipio": "Madrid"
        }), 200

    try:
        lat_res = location_data["lat"]
        lon_res = location_data["lon"]
        fuente = location_data.get("source", "unknown")

        # 3. Obtención de datos reales de AEMET
        raw_data = obtener_clima_por_coordenadas(lat_res, lon_res)
        
        # 4. Normalización
        data_normalizada = normalizar_datos_aemet(raw_data, fuente_ubicacion=fuente)
        
        # 5. Evaluación de alertas (desde config JSON)
        alertas_service = get_alert_service()
        data_normalizada["alertas"] = alertas_service.get_alertas_activas(data_normalizada)
        data_normalizada["alerta_nivel"] = alertas_service.get_nivel_maximo(data_normalizada)
        
        # 6. Información de ubicación
        data_normalizada["_ubicacion"] = {
            "ciudad": location_data.get("ciudad"),
            "provincia": location_data.get("provincia"),
            "fuente_localizacion": fuente
        }
        
        # 7. Persistencia
        if data_normalizada:
            exito_guardado = append(data_normalizada)
            if exito_guardado:
                log_info(f"Registro guardado: {data_normalizada.get('municipio')} ({fuente})")
        
        return jsonify(data_normalizada), 200

    except Exception as e:
        log_error(f"Error crítico en el Gateway /api/clima: {e}")
        return jsonify({
            "error": "Error interno del servidor", 
            "details": str(e)
        }), 500


@app.route("/api/clima/<ciudad>")
def api_clima_ciudad(ciudad):
    """
    Endpoint para obtener clima por nombre de ciudad.
    Ejemplo: /api/clima/Madrid
    """
    try:
        raw_data = obtener_clima_por_municipio(ciudad)
        if not raw_data:
            return jsonify({"error": "Ciudad no encontrada"}), 404
        
        data_normalizada = normalizar_datos_aemet(raw_data, fuente_ubicacion="geocode")
        
        alertas_service = get_alert_service()
        data_normalizada["alertas"] = alertas_service.get_alertas_activas(data_normalizada)
        data_normalizada["alerta_nivel"] = alertas_service.get_nivel_maximo(data_normalizada)
        
        return jsonify(data_normalizada), 200
    except Exception as e:
        log_error(f"Error en /api/clima/{ciudad}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/geo/<ciudad>")
def api_geo_ciudad(ciudad):
    """
    Geocodifica una ciudad (obtiene coordenadas).
    Ejemplo: /api/geo/Madrid
    """
    info = get_city_info(ciudad)
    if not info:
        return jsonify({"error": "Ciudad no encontrada"}), 404
    return jsonify(info), 200


@app.route("/api/health")
def api_health():
    """
    Health check - verifica el estado de la API.
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0"
    }), 200


@app.route("/api/alertas")
def api_alertas():
    """
    Lista todas las alertas configuradas.
    """
    from pathlib import Path
    config_path = Path("config/alertas.json")
    if config_path.exists():
        import json
        with open(config_path, "r") as f:
            config = json.load(f)
        return jsonify(config.get("alertas", {})), 200
    return jsonify({"error": "Configuración no encontrada"}), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)