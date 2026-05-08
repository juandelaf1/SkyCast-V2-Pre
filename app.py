from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import os
from datetime import datetime
from functools import wraps

# Importamos controladores
from controllers.view_controller import view_bp
from controllers.manual_controller import manual_bp 

# Importamos servicios
from services.weather_api_service import obtener_clima_por_coordenadas, obtener_clima_por_municipio
from services.normalizer_service import normalizar_datos_aemet
from services.geolocation_service import resolve_location, get_city_info, reverse_geocode
from services.alert_service import get_alert_service
from services.logging_service import log_info, log_error, log_warning
from services.rate_limiter import check_rate_limit, rate_limit
from repositories.json_repository import append            

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_secreta")

# Registro de Blueprints
app.register_blueprint(view_bp)
app.register_blueprint(manual_bp)


def _validar_coordenadas(lat, lon) -> bool:
    """Valida que las coordenadas sean válidas."""
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False


@app.route("/api/clima")
def api_clima():
    """
    Gateway principal: Geolocalización + Clima + Alertas.
    Fuentes: IP-API.com (geo), AEMET (clima), OMM (umbrales)
    """
    # Rate limiting
    allowed, limit_info = check_rate_limit("api_clima")
    if not allowed:
        return jsonify(limit_info), 429
    
    # Extract parameters
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    ciudad = request.args.get('ciudad')

    # Fallback: IP geolocation
    if not lat and not lon and not ciudad:
        from services.geolocation_service import get_geolocation_service
        geo = get_geolocation_service()
        ip_loc = geo.get_location_by_ip()
        if ip_loc:
            lat = ip_loc.get("lat")
            lon = ip_loc.get("lon")

    # Resolve location
    location = resolve_location(
        lat=float(lat) if lat else None,
        lon=float(lon) if lon else None,
        city=ciudad
    )

    # Fallback if no location
    if not location or not location.get("lat"):
        return jsonify({
            "status": "error",
            "message": "Ubicación no resuelta",
            "suggestion": "Proporciona lat/lon o ciudad"
        }), 400

    # Get weather data
    try:
        raw_data = obtener_clima_por_coordenadas(
            location["lat"], 
            location["lon"]
        )
        
        if not raw_data:
            return jsonify({
                "status": "error",
                "message": "Sin datos meteorológicos disponibles"
            }), 503
        
        # Normalize
        fuente = location.get("source", "unknown")
        data = normalizar_datos_aemet(raw_data, fuente_ubicacion=fuente)
        
        # Add alerts from config
        alertas = get_alert_service()
        data["alertas"] = alertas.get_alertas_activas(data)
        data["alerta_nivel"] = alertas.get_nivel_maximo(data)
        
        # Add location metadata
        data["_ubicacion"] = {
            "ciudad": location.get("ciudad"),
            "provincia": location.get("provincia"),
            "fuente_localizacion": fuente
        }
        
        # Add metadata
        data["_metadata"] = raw_data.get("_metadata", {})
        data["_timestamp"] = datetime.now().isoformat()
        
        # Save to repository
        append(data)
        
        log_info(f"Clima devuelto: {data.get('municipio')} ({fuente})")
        
        return jsonify(data), 200
        
    except Exception as e:
        log_error(f"Error en /api/clima: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno",
            "details": str(e)
        }), 500


@app.route("/api/clima/<ciudad>")
def api_clima_ciudad(ciudad):
    """Get weather by city name."""
    allowed, limit_info = check_rate_limit("api_clima")
    if not allowed:
        return jsonify(limit_info), 429
    
    try:
        raw_data = obtener_clima_por_municipio(ciudad)
        if not raw_data:
            return jsonify({"error": f"Ciudad no encontrada: {ciudad}"}), 404
        
        data = normalizar_datos_aemet(raw_data, "geocode")
        
        alertas = get_alert_service()
        data["alertas"] = alertas.get_alertas_activas(data)
        data["alerta_nivel"] = alertas.get_nivel_maximo(data)
        
        return jsonify(data), 200
        
    except Exception as e:
        log_error(f"Error en /api/clima/{ciudad}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/geo/<ciudad>")
def api_geo(ciudad):
    """Geocode a city name to coordinates."""
    allowed, limit_info = check_rate_limit("api_geo")
    if not allowed:
        return jsonify(limit_info), 429
    
    info = get_city_info(ciudad)
    if not info:
        return jsonify({"error": f"Ciudad no encontrada: {ciudad}"}), 404
    
    return jsonify(info), 200


@app.route("/api/health")
def api_health():
    """Health check endpoint."""
    from services.rate_limiter import get_rate_status
    
    rate_status = get_rate_status()
    
    return jsonify({
        "status": "healthy",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "rate_limiting": rate_status
    }), 200


@app.route("/api/alertas")
def api_alertas_config():
    """Get alert configuration."""
    from pathlib import Path
    import json
    
    config_path = Path("config/alertas.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
        return jsonify(config.get("alertas", {})), 200
    
    return jsonify({"error": "Config not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)