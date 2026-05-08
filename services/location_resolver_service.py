import json
import os
from pathlib import Path
from services.logging_service import log_info, log_warning

CITIES_FILE = Path("config/ciudades.json")

_ciudades_cache = None


def _load_cities():
    """Carga ciudades desde archivo JSON o usa fallback."""
    global _ciudades_cache
    if _ciudades_cache is not None:
        return _ciudades_cache
    
    if CITIES_FILE.exists():
        try:
            with open(CITIES_FILE, "r", encoding="utf-8") as f:
                _ciudades_cache = json.load(f)
            log_info(f"Ciudades cargadas desde {CITIES_FILE}")
            return _ciudades_cache
        except Exception as e:
            log_warning(f"Error cargando ciudades: {e}")
    
    _ciudades_cache = _get_default_cities()
    return _ciudades_cache


def _get_default_cities():
    """Ciudades por defecto (capitales de provincia)."""
    return {
        "madrid": {"lat": 40.4167, "lon": -3.7033, "provincia": "Madrid"},
        "barcelona": {"lat": 41.3851, "lon": 2.1734, "provincia": "Barcelona"},
        "valencia": {"lat": 39.4699, "lon": -0.3763, "provincia": "Valencia"},
        "sevilla": {"lat": 37.3891, "lon": -5.9845, "provincia": "Sevilla"},
        "málaga": {"lat": 36.7213, "lon": -4.4214, "provincia": "Málaga"},
        "córdoba": {"lat": 37.8888, "lon": -4.7794, "provincia": "Córdoba"},
        "granada": {"lat": 37.1773, "lon": -3.5986, "provincia": "Granada"},
        "huelva": {"lat": 37.2614, "lon": -6.9448, "provincia": "Huelva"},
        "cádiz": {"lat": 36.5271, "lon": -6.2886, "provincia": "Cádiz"},
        "almería": {"lat": 36.8340, "lon": -2.4517, "provincia": "Almería"},
        "tarragona": {"lat": 41.1153, "lon": 1.2539, "provincia": "Tarragona"},
        "girona": {"lat": 41.9794, "lon": 2.8214, "provincia": "Girona"},
        "lleida": {"lat": 41.6176, "lon": 0.6202, "provincia": "Lleida"},
        "alicante": {"lat": 38.3452, "lon": -0.4810, "provincia": "Alicante"},
        "castellón": {"lat": 39.9713, "lon": -0.0321, "provincia": "Castellón"},
        "a Coruña": {"lat": 43.3623, "lon": -8.3965, "provincia": "A Coruña"},
        "vigo": {"lat": 42.2408, "lon": -8.7207, "provincia": "Pontevedra"},
        "ourense": {"lat": 42.3355, "lon": -7.8638, "provincia": "Ourense"},
        "lugo": {"lat": 43.0108, "lon": -7.5558, "provincia": "Lugo"},
        "santiago de compostela": {"lat": 42.8782, "lon": -8.5448, "provincia": "A Coruña"},
        "valladolid": {"lat": 41.6351, "lon": -4.7195, "provincia": "Valladolid"},
        "burgos": {"lat": 42.3439, "lon": -3.6969, "provincia": "Burgos"},
        "león": {"lat": 42.5997, "lon": -5.5705, "provincia": "León"},
        "salamanca": {"lat": 40.9702, "lon": -5.6635, "provincia": "Salamanca"},
        "palencia": {"lat": 42.0096, "lon": -4.4876, "provincia": "Palencia"},
        "segovia": {"lat": 40.9429, "lon": -4.1083, "provincia": "Segovia"},
        "ávila": {"lat": 40.2822, "lon": -4.9255, "provincia": "Ávila"},
        "soria": {"lat": 41.7640, "lon": -2.4789, "provincia": "Soria"},
        "zamora": {"lat": 41.5033, "lon": -5.5707, "provincia": "Zamora"},
        "toledo": {"lat": 39.8678, "lon": -4.0167, "provincia": "Toledo"},
        "albacete": {"lat": 38.9943, "lon": -1.8588, "provincia": "Albacete"},
        "cuenca": {"lat": 40.0701, "lon": -2.1374, "provincia": "Cuenca"},
        "guadalajara": {"lat": 40.6326, "lon": -3.1673, "provincia": "Guadalajara"},
        "ciudad real": {"lat": 38.9864, "lon": -3.9302, "provincia": "Ciudad Real"},
        "bilbao": {"lat": 43.2630, "lon": -2.9350, "provincia": "Bizkaia"},
        "vitoria": {"lat": 42.8125, "lon": -2.6727, "provincia": "Araba"},
        "donostia": {"lat": 43.3203, "lon": -1.9818, "provincia": "Gipuzkoa"},
        "oviedo": {"lat": 43.3619, "lon": -5.8494, "provincia": "Asturias"},
        "gijón": {"lat": 43.5423, "lon": -5.6761, "provincia": "Asturias"},
        "santander": {"lat": 43.4623, "lon": -3.8099, "provincia": "Cantabria"},
        "pamplona": {"lat": 42.8125, "lon": -1.6458, "provincia": "Navarra"},
        "logroño": {"lat": 42.4637, "lon": -2.4450, "provincia": "La Rioja"},
        "zaragoza": {"lat": 41.6488, "lon": -0.8891, "provincia": "Zaragoza"},
        "huesca": {"lat": 42.1315, "lon": -0.4077, "provincia": "Huesca"},
        "teruel": {"lat": 40.3456, "lon": -1.1061, "provincia": "Teruel"},
        "badajoz": {"lat": 38.8743, "lon": -6.9538, "provincia": "Badajoz"},
        "cáceres": {"lat": 39.4735, "lon": -6.3770, "provincia": "Cáceres"},
        "murcia": {"lat": 37.9838, "lon": -1.1445, "provincia": "Murcia"},
        "cartagena": {"lat": 37.6067, "lon": -0.9850, "provincia": "Murcia"},
        "las palmas": {"lat": 28.1248, "lon": -15.4466, "provincia": "Las Palmas"},
        "santa cruz de tenerife": {"lat": 28.4636, "lon": -16.2518, "provincia": "Santa Cruz de Tenerife"},
        "palma": {"lat": 39.5696, "lon": 2.6502, "provincia": "Islas Baleares"},
        "ceuta": {"lat": 35.8894, "lon": -5.3215, "provincia": "Ceuta"},
        "melilla": {"lat": 35.2938, "lon": -2.9386, "provincia": "Melilla"},
    }


def resolve_location(lat=None, lon=None, city=None):
    """
    Failover: GPS -> Ciudad -> Default (Madrid).
    """
    def is_valid(value):
        return value and str(value).lower() not in ["none", "null", "undefined", ""]

    # GPS directo
    if is_valid(lat) and is_valid(lon):
        try:
            log_info(f"Ubicación por GPS: {lat}, {lon}")
            return {"lat": float(lat), "lon": float(lon), "source": "GPS", "success": True}
        except ValueError:
            log_warning(f"Coordenadas inválidas: {lat}, {lon}")

    # Ciudad
    if is_valid(city):
        city_clean = str(city).strip().lower()
        ciudades = _load_cities()
        
        if city_clean in ciudades:
            log_info(f"Ubicación resuelta: {city_clean}")
            coords = ciudades[city_clean]
            return {"lat": coords["lat"], "lon": coords["lon"], "source": "MANUAL", "success": True}
        
        log_warning(f"Ciudad no encontrada: {city}")

    # Fallback Madrid
    log_info("Fallback: Madrid")
    return {"lat": 40.4530, "lon": -3.6883, "source": "DEFAULT", "success": True}


def get_available_cities():
    """Devuelve lista de ciudades disponibles."""
    return list(_load_cities().keys())


def search_city(query):
    """Busca ciudades que contengan el query."""
    ciudades = _load_cities()
    query = query.lower()
    return [c for c in ciudades if query in c.lower()]