"""
ClimApp-Analytics-Pro - API de Clima en Tiempo Real
==============================================
API REST para obtener datos meteorológicos de AEMET.
- Geolocalización: IP-API.com + Nominatim
- Clima: AEMET OpenData
- Alertas: Umbrales configurables
"""

from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import os
import time
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
from services.rate_limiter import check_rate_limit, get_rate_status
from repositories.json_repository import append            

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave_secreta")
app.config["JSON_SORT_KEYS"] = False

# Registro de Blueprints
app.register_blueprint(view_bp)
app.register_blueprint(manual_bp)


# ==== MÉTRICAS GLOBALES ====
_metrics = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "start_time": time.time()
}


def _increment_metric(endpoint: str):
    """Incrementa métricas de uso."""
    _metrics["requests_total"] += 1
    if endpoint not in _metrics["requests_by_endpoint"]:
        _metrics["requests_by_endpoint"][endpoint] = 0
    _metrics["requests_by_endpoint"][endpoint] += 1


def _validar_coordenadas(lat, lon) -> bool:
    """Valida que las coordenadas sean válidas."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        return -90 <= lat_f <= 90 and -180 <= lon_f <= 180
    except (TypeError, ValueError):
        return False


# ==== ENDPOINTS ====

@app.route("/api/clima")
def api_clima():
    """
    Gateway principal: Geolocalización + Clima + Alertas.
    
    Parámetros (todos opcionales):
    - lat: Latitud decimal (ej: 40.4167)
    - lon: Longitud decimal (ej: -3.7033)
    - ciudad: Nombre del municipio (ej: Madrid)
    
    Returns: JSON con datos meteorológicos
    """
    _increment_metric("/api/clima")
    
    # Rate limiting
    allowed, limit_info = check_rate_limit("api_clima")
    if not allowed:
        return jsonify({
            "error": "Rate limit excedido",
            "limite": limit_info["limite"],
            "ventana_segundos": limit_info["ventana"]
        }), 429
    
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
            ciudad = ip_loc.get("ciudad", "")

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
            "codigo": "LOC_NOT_RESOLVED",
            "mensaje": "No se pudo resolver la ubicación",
            "sugerencia": "Proporciona lat/lon o nombre de ciudad"
        }), 400

    # Get weather data
    try:
        raw_data = obtener_clima_por_coordenadas(
            location["lat"], 
            location["lon"]
        )
        
        if not raw_data:
            return jsonify({
                "status": "no_data",
                "ubicacion": {
                    "lat": location["lat"],
                    "lon": location["lon"],
                    "ciudad": location.get("ciudad")
                },
                "mensaje": "Sin datos meteorológicos disponibles",
                "sugerencia": "Intenta más tarde o con otras coordenadas"
            }), 503
        
        # Normalize
        fuente = location.get("source", "unknown")
        data = normalizar_datos_aemet(raw_data, fuente_ubicacion=fuente)
        
        # Add alerts from config
        alertas = get_alert_service()
        data["alertas"] = alertas.get_alertas_activas(data)
        data["alerta_nivel"] = alertas.get_nivel_maximo(data)
        
        # Add extended location metadata
        data["_ubicacion"] = {
            "ciudad": location.get("ciudad"),
            "provincia": location.get("provincia"),
            "codigo_postal": location.get("codigo_postal"),
            "pais": location.get("pais"),
            "fuente_localizacion": fuente
        }
        
        # Add full metadata
        data["_metadata"] = {
            "estacion": raw_data.get("ubi"),
            "estacion_id": raw_data.get("estacion_id"),
            "estacion_distancia_km": raw_data.get("_metadata", {}).get("estacion_distancia_km"),
            "fuente_datos": "AEMET",
            "tipo_respuesta": "fallback" if raw_data.get("_fallback") else "live",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(time.time() - _metrics["start_time"])
        }
        
        # Add status
        data["status"] = "ok"
        
        # Save to repository
        append(data)
        
        log_info(f"API: {data.get('municipio')} - Temp: {data.get('temperatura')}C")
        
        return jsonify(data), 200
        
    except Exception as e:
        log_error(f"API Error /api/clima: {e}")
        return jsonify({
            "status": "error",
            "codigo": "INTERNAL_ERROR",
            "mensaje": "Error interno del servidor",
            "detalle": str(e)
        }), 500


@app.route("/api/clima/<ciudad>")
def api_clima_ciudad(ciudad):
    """Obtiene clima por nombre de ciudad."""
    _increment_metric("/api/clima/<ciudad>")
    
    allowed, limit_info = check_rate_limit("api_clima")
    if not allowed:
        return jsonify(limit_info), 429
    
    try:
        raw_data = obtener_clima_por_municipio(ciudad)
        if not raw_data:
            return jsonify({
                "error": f"Ciudad no encontrada: {ciudad}"
            }), 404
        
        data = normalizar_datos_aemet(raw_data, "geocode")
        
        alertas = get_alert_service()
        data["alertas"] = alertas.get_alertas_activas(data)
        data["alerta_nivel"] = alertas.get_nivel_maximo(data)
        data["status"] = "ok"
        
        return jsonify(data), 200
        
    except Exception as e:
        log_error(f"API Error /api/clima/{ciudad}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/geo/<ciudad>")
def api_geo(ciudad):
    """Geocodifica una ciudad a coordenadas."""
    _increment_metric("/api/geo/<ciudad>")
    
    allowed, limit_info = check_rate_limit("api_geo")
    if not allowed:
        return jsonify(limit_info), 429
    
    info = get_city_info(ciudad)
    if not info:
        return jsonify({
            "error": f"Ciudad no encontrada: {ciudad}"
        }), 404
    
    return jsonify(info), 200


@app.route("/api/health")
def api_health():
    """Health check con métricas."""
    _increment_metric("/api/health")
    
    uptime = int(time.time() - _metrics["start_time"])
    
    return jsonify({
        "status": "healthy",
        "version": "2.1",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime,
        "requests": {
            "total": _metrics["requests_total"],
            "by_endpoint": _metrics["requests_by_endpoint"]
        },
        "rate_limiting": get_rate_status()
    }), 200


@app.route("/api/stats")
def api_stats():
    """Estadísticas de uso de la API."""
    _increment_metric("/api/stats")
    
    from repositories.json_repository import filter_records
    
    try:
        # Get recent records
        registros = filter_records(fecha="2026-05-08")
        
        # Calculate stats
        temps = [r.get("temperatura", 0) for r in registros if r.get("temperatura")]
        hums = [r.get("humedad", 0) for r in registros if r.get("humedad")]
        
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "metricas_api": {
                "requests_total": _metrics["requests_total"],
                "uptime_seconds": int(time.time() - _metrics["start_time"])
            },
            "datos_hoy": {
                "registros": len(registros),
                "temp_promedio": round(sum(temps) / len(temps), 1) if temps else None,
                "humedad_promedio": round(sum(hums) / len(hums), 1) if hums else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "ok", 
            "metricas_api": {
                "requests_total": _metrics["requests_total"],
                "uptime_seconds": int(time.time() - _metrics["start_time"])
            }
        }), 200


@app.route("/api/alertas")
def api_alertas_config():
    """Get alert configuration."""
    _increment_metric("/api/alertas")
    
    from pathlib import Path
    import json
    
    config_path = Path("config/alertas.json")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return jsonify(config.get("alertas", {})), 200
    
    return jsonify({"error": "Config not found"}), 404


@app.route("/")
def index():
    """Página principal."""
    return render_template("index.html")


# ==== ERROR HANDLERS ====

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": " Endpoint no encontrado",
        "codigo": 404,
        "sugerencia": "Usa /api/clima, /api/geo, /api/health, /api/alertas"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    log_error(f"Unhandled error: {e}")
    return jsonify({
        "error": "Error interno",
        "codigo": 500
    }), 500


if __name__ == "__main__":
    print("=" * 50)
    print("ClimApp-Analytics-Pro v2.1")
    print("=" * 50)
    print("Endpoints:")
    print("  /api/clima              - Clima por lat/lon/IP")
    print("  /api/clima/<ciudad>    - Clima por ciudad")
    print("  /api/geo/<ciudad>     - Geocodificar")
    print("  /api/health           - Health check")
    print("  /api/stats            - Estadisticas")
    print("  /api/alertas          - Config alertas")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)