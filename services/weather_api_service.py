import os
import json
import logging
import time
import random
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "cache_aemet.json"
CACHE_MAX_AGE = 3600


def _load_cache() -> Optional[Dict]:
    """Carga el caché si existe y no ha expirado."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        edad = time.time() - cache.get("timestamp", 0)
        if edad > CACHE_MAX_AGE:
            return None
        return cache.get("data")
    except Exception:
        return None


def _save_cache(data: List) -> None:
    """Guarda los datos en caché."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "data": data}, f, indent=2)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error guardando caché: {e}")


class WeatherAPIService:
    def __init__(self, timeout: int = 20, use_cache: bool = True):
        self.api_key = os.getenv("AEMET_API_KEY")
        if not self.api_key:
            raise ValueError("AEMET_API_KEY no encontrada en .env")
        
        self.timeout = int(os.getenv("AEMET_TIMEOUT", str(timeout)))
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ClimApp-Analytics-Pro/1.0"})
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"

    def _obtener_datos_crudos(self) -> list:
        """Obtiene todas las observaciones de AEMET con fallback a caché."""
        headers = {"api_key": self.api_key, "cache-control": "no-cache"}
        
        if self.use_cache:
            cached = _load_cache()
            if cached:
                self.logger.info("Usando datos desde caché (offline)")
                return cached
        
        try:
            res_meta = self.session.get(self.base_url, headers=headers, timeout=self.timeout)
            res_meta.raise_for_status()
            
            datos_url = res_meta.json().get("datos")
            if not datos_url:
                cached = _load_cache()
                return cached if cached else []
            
            res_datos = self.session.get(datos_url, timeout=self.timeout)
            res_datos.raise_for_status()
            data = res_datos.json()
            
            if self.use_cache and data:
                _save_cache(data)
            
            return data
        except Exception as e:
            self.logger.error(f"Error al conectar con AEMET: {e}")
            cached = _load_cache()
            return cached if cached else []

    def obtener_clima_por_coordenadas(self, user_lat: float, user_lon: float) -> Optional[Dict[str, Any]]:
        """
        Localiza la estación más cercana y devuelve sus datos.
        Si AEMET falla o estación >50km, usa fallback avanzado.
        """
        observaciones = self._obtener_datos_crudos()
        
        if not observaciones:
            self.logger.warning("No se recibieron observaciones de AEMET.")
            return self._generar_fallback(user_lat, user_lon)

        estacion_cercana = None
        distancia_minima = float('inf')

        for obs in observaciones:
            try:
                obs_lat = float(obs['lat'])
                obs_lon = float(obs['lon'])

                from utils.helpers import calcular_distancia
                dist = calcular_distancia(float(user_lat), float(user_lon), obs_lat, obs_lon)

                if dist < distancia_minima:
                    distancia_minima = dist
                    estacion_cercana = obs

            except (KeyError, ValueError, TypeError):
                continue

        if estacion_cercana:
            self.logger.info(f"Estación más cercana: {estacion_cercana.get('ubi')} ({distancia_minima:.2f}km)")
        
        # Si estación está a más de 50km, usar fallback
        if distancia_minima > 50:
            self.logger.warning(f"Estación a {distancia_minima:.2f}km (>50km). Usando fallback.")
            return self._generar_fallback(user_lat, user_lon, estacion_cercana)

        return estacion_cercana

    def _generar_fallback(self, lat: float, lon: float, estacion=None) -> Dict[str, Any]:
        """
        Genera datos de fallback cuando AEMET falla.
        Intenta usar geolocalización por IP como última opción.
        """
        from services.geolocation_service import get_geolocation_service, reverse_geocode
        
        # Intentar obtener información de ubicación
        city_info = None
        if lat and lon:
            try:
                city_info = reverse_geocode(lat, lon)
            except Exception:
                pass
        
        # Generar datos sintéticos razonables
        return {
            "estacion_id": "FALLBACK-" + (city_info.get("ciudad", "UNKNOWN").replace(' ', '-') if city_info else "EMERGENCIA"),
            "ubi": city_info.get("ciudad", "Ubicación Fallback") if city_info else "Datos de emergencia",
            "lat": float(lat),
            "lon": float(lon),
            "municipio": city_info.get("ciudad") if city_info else None,
            "provincia": city_info.get("provincia") if city_info else None,
            "codigo_postal": city_info.get("codigo_postal") if city_info else None,
            "temperatura": round(random.uniform(15, 28), 1),
            "humedad": random.randint(40, 70),
            "viento": round(random.uniform(0, 15), 1),
            "presion": random.randint(1010, 1025),
            "lluvia": 0,
            "fuente": "fallback",
            "_fallback": True
        }

    def obtener_clima_por_id(self, station_id: str) -> Optional[Dict]:
        """Obtiene datos por ID de estación."""
        observaciones = self._obtener_datos_crudos()
        for obs in observaciones:
            if obs.get("id") == station_id:
                return obs
        return None
    
    def obtener_clima_por_municipio(self, municipio: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene clima usando el nombre del municipio.
        Primero geocodifica, luego busca estación más cercana.
        """
        from services.geolocation_service import geocode_city
        
        # Geocodificar municipio
        location = geocode_city(municipio)
        if not location:
            return None
        
        # Buscar estación más cercana
        return self.obtener_clima_por_coordenadas(location["lat"], location["lon"])


def obtener_clima_por_coordenadas(lat, lon, use_cache: bool = True):
    """Función puente para app.py."""
    timeout = int(os.getenv("AEMET_TIMEOUT", "20"))
    service = WeatherAPIService(timeout=timeout, use_cache=use_cache)
    return service.obtener_clima_por_coordenadas(lat, lon)


def obtener_clima_por_municipio(municipio: str):
    """Función para obtener clima por nombre de municipio."""
    service = WeatherAPIService()
    return service.obtener_clima_por_municipio(municipio)