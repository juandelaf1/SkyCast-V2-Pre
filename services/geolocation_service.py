import os
import json
import logging
import time
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

IP_API_URL = "http://ip-api.com/json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"

INE_CODIGOS_URL = "https://www.ine.es/dyngs/INEBase/ficheros/allca.zip"


class GeolocationService:
    """
    Servicio de geolocalización basado en fuentes oficiales.
    No hardcodeado - obtiene datos de APIs reales.
    """
    
    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self.cache_dir = Path("data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ClimApp-Analytics-Pro/1.0"
        })
    
    def _load_cache(self, key: str) -> Optional[Dict]:
        """Carga datos desde caché si no ha expirado."""
        cache_file = self.cache_dir / f"geo_{key}.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            
            edad = time.time() - cache.get("timestamp", 0)
            if edad > self.cache_ttl:
                return None
            
            return cache.get("data")
        except Exception:
            return None
    
    def _save_cache(self, key: str, data: Dict) -> None:
        """Guarda datos en caché."""
        cache_file = self.cache_dir / f"geo_{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"timestamp": time.time(), "data": data}, f, indent=2)
        except Exception as e:
            logger.warning(f"Error guardando caché: {e}")
    
    def get_location_by_ip(self, ip: str = None) -> Dict:
        """
        Obtiene ubicación por IP usando ip-api.com (fuente oficial gratuita).
        Sin parámetros = IP actual del servidor.
        """
        cache_key = f"ip_{ip or 'auto'}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{IP_API_URL}/{ip}" if ip else IP_API_URL
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                result = {
                    "ip": data.get("query"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "ciudad": data.get("city"),
                    "region": data.get("regionName"),
                    "pais": data.get("country"),
                    "pais_code": data.get("countryCode"),
                    "isp": data.get("isp"),
                    "org": data.get("org"),
                    "timezone": data.get("timezone"),
                    "source": "ip-api.com"
                }
                self._save_cache(cache_key, result)
                return result
            
        except Exception as e:
            logger.error(f"Error en IP geolocation: {e}")
        
        return self._get_default_location()
    
    def _get_default_location(self) -> Dict:
        """Ubicación por defecto (Madrid) cuando falha todo."""
        return {
            "lat": 40.4167,
            "lon": -3.7033,
            "ciudad": "Madrid",
            "region": "Comunidad de Madrid",
            "pais": "España",
            "source": "default"
        }
    
    def geocode_city(self, city: str, country: str = "España") -> Optional[Dict]:
        """
        Geocodifica una ciudad usando Nominatim (OpenStreetMap - fuente oficial OSM).
        """
        cache_key = f"geocode_{city.lower().replace(' ', '_')}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        
        try:
            params = {
                "q": f"{city}, {country}",
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }
            response = self.session.get(NOMINATIM_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data:
                loc = data[0]
                result = {
                    "lat": float(loc.get("lat")),
                    "lon": float(loc.get("lon")),
                    "nombre": loc.get("display_name"),
                    "tipo": loc.get("type"),
                    "importancia": float(loc.get("importance", 0)),
                    "_source": "nominatim.openstreetmap.org"
                }
                
                address = loc.get("address", {})
                result["ciudad"] = address.get("city") or address.get("town") or address.get("village")
                result["provincia"] = address.get("county") or address.get("state")
                result["codigo_postal"] = address.get("postcode")
                result["pais"] = address.get("country")
                
                self._save_cache(cache_key, result)
                return result
            
        except Exception as e:
            logger.error(f"Error en geocoding: {e}")
        
        return None
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Obtiene información de ubicación a partir de coordenadas.
        Útil para mostrar nombre friendly al usuario.
        """
        cache_key = f"reverse_{lat}_{lon}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "addressdetails": 1
            }
            response = self.session.get(NOMINATIM_REVERSE, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data:
                address = data.get("address", {})
                result = {
                    "lat": lat,
                    "lon": lon,
                    "ciudad": address.get("city") or address.get("town") or address.get("village"),
                    "provincia": address.get("county") or address.get("state"),
                    "codigo_postal": address.get("postcode"),
                    "pais": address.get("country"),
                    "nombre": data.get("display_name"),
                    "source": "nominatim.openstreetmap.org"
                }
                self._save_cache(cache_key, result)
                return result
            
        except Exception as e:
            logger.error(f"Error en reverse geocoding: {e}")
        
        return None


_geo_service = None


def get_geolocation_service() -> GeolocationService:
    """Obtiene instancia singleton del servicio."""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeolocationService()
    return _geo_service


def resolve_location(lat: float = None, lon: float = None, city: str = None) -> Dict:
    """
    Resuelve ubicación usando fuentes oficiales.
    Prioridad: GPS > IP > Ciudad > Default
    """
    # 1. Coordenadas GPS directas
    if lat and lon:
        return {
            "lat": float(lat),
            "lon": float(lon),
            "source": "gps"
        }
    
    # 2. Ciudad especificada - usar Nominatim
    if city:
        service = get_geolocation_service()
        result = service.geocode_city(city)
        if result:
            result["source"] = "geocode"
            return result
    
    # 3. Por IP - usar ip-api.com
    service = get_geolocation_service()
    ip_location = service.get_location_by_ip()
    if ip_location:
        ip_location["source"] = "ip"
        return ip_location
    
    # 4. Default Madrid
    return service._get_default_location()


def get_city_info(city: str) -> Optional[Dict]:
    """Obtiene información detallada de una ciudad."""
    service = get_geolocation_service()
    return service.geocode_city(city)


def reverse_geocode(lat: float, lon: float) -> Optional[Dict]:
    """Obtiene información de ubicación por coordenadas."""
    service = get_geolocation_service()
    return service.reverse_geocode(lat, lon)