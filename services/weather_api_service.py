"""
Weather API Service - ClimApp-Analytics-Pro
====================================
Servicio de clima basado en AEMET OpenData.
- Busca estación más cercana geográfica
- Usa validaciones estrictas de datos
- Fallback automático robusto
"""

import os
import json
import logging
import time
import random
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "cache_aemet.json"
CACHE_MAX_AGE = 1800  # 30 minutos


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


def _validar_dato_meteorologico(key: str, value: Any) -> Tuple[bool, float]:
    """
    Valida un dato meteorológico.
    Returns: (es_valido, valor_convertido)
    """
    if value is None or value == "" or str(value).strip() == "":
        return False, 0.0
    
    # Manejar valores especiales
    val_str = str(value).strip()
    if val_str.lower() in ("ip", "Ip", "iP", "vp", "Vp", "trace"):
        return True, 0.0  # Precipitación inapreciable
    
    try:
        val = float(val_str)
        
        # Rangos válidos según AEMET/OMM
        rangos_validos = {
            "ta": (-50, 60),      # Temperatura °C
            "hr": (0, 100),       # Humedad %
            "vv": (0, 200),      # Viento km/h
            "prec": (0, 500),     # Lluvia mm
            "pres": (900, 1060),  # Presión hPa
        }
        
        if key in rangos_validos:
            min_val, max_val = rangos_validos[key]
            if min_val <= val <= max_val:
                return True, val
            return False, val
        
        return True, val
    except (ValueError, TypeError):
        return False, 0.0


class WeatherAPIService:
    """Servicio de clima con AEMET."""
    
    def __init__(self, timeout: int = 20, use_cache: bool = True):
        self.api_key = os.getenv("AEMET_API_KEY")
        if not self.api_key:
            raise ValueError("AEMET_API_KEY no encontrada en .env")
        
        self.timeout = int(os.getenv("AEMET_TIMEOUT", str(timeout)))
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ClimApp-Analytics-Pro/1.0",
            "Accept": "application/json"
        })
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"

    def _obtener_datos_crudos(self) -> list:
        """Obtiene observaciones de AEMET con retry y caché."""
        headers = {"api_key": self.api_key}
        
        # Intentar caché primero
        if self.use_cache:
            cached = _load_cache()
            if cached:
                self.logger.info("Usando datos desde caché")
                return cached
        
        try:
            # Primera запрос: obtener URL de datos
            res_meta = self.session.get(self.base_url, headers=headers, timeout=self.timeout)
            res_meta.raise_for_status()
            
            datos_url = res_meta.json().get("datos")
            if not datos_url:
                self.logger.warning("AEMET no proporcionó URL de datos")
                cached = _load_cache()
                return cached if cached else []
            
            # Segunda petición: obtener datos reales
            res_datos = self.session.get(datos_url, timeout=self.timeout)
            res_datos.raise_for_status()
            data = res_datos.json()
            
            # Guardar en caché
            if self.use_cache and data:
                _save_cache(data)
            
            self.logger.info(f"Datos de AEMET obtenidos: {len(data)} estaciones")
            return data
            
        except requests.exceptions.Timeout:
            self.logger.error("Timeout conectando con AEMET")
            cached = _load_cache()
            return cached if cached else []
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error de red con AEMET: {e}")
            cached = _load_cache()
            return cached if cached else []
            
        except Exception as e:
            self.logger.error(f"Error inesperado con AEMET: {e}")
            cached = _load_cache()
            return cached if cached else []

    def _buscar_estacion_cercana(self, user_lat: float, user_lon: float, 
                             observaciones: list, max_distancia: float = 100) -> Tuple[Optional[Dict], float]:
        """
        Busca la estación meteorológica más cercana.
        Returns: (estacion, distancia_en_km)
        """
        from utils.helpers import calcular_distancia
        
        mejor_estacion = None
        distancia_min = float('inf')
        
        for obs in observaciones:
            try:
                # Validar coordenadas
                lat_str = obs.get("lat")
                lon_str = obs.get("lon")
                
                if not lat_str or not lon_str:
                    continue
                
                obs_lat = float(lat_str)
                obs_lon = float(lon_str)
                
                # Calcular distancia
                dist = calcular_distancia(float(user_lat), float(user_lon), obs_lat, obs_lon)
                
                if dist < distancia_min:
                    distancia_min = dist
                    mejor_estacion = obs
                    
            except (KeyError, ValueError, TypeError):
                continue
        
        # Filtrar por distancia máxima
        if distancia_min > max_distancia:
            self.logger.warning(f"Estación más cercana a {distancia_min:.1f}km > {max_distancia}km")
            return None, distancia_min
        
        return mejor_estacion, distancia_min if mejor_estacion else float('inf')

    def _procesar_estacion(self, estacion: Dict) -> Dict:
        """Procesa y valida datos de una estación."""
        datos_procesados = {
            "estacion_id": estacion.get("id", "DESCONOCIDA"),
            "ubi": estacion.get("ubi", "Desconocida"),
            "lat": estacion.get("lat"),
            "lon": estacion.get("lon"),
            "fint": estacion.get("fint"),  # Fecha/hora
        }
        
        # Procesar cada variable
        variables = [
            ("ta", "temperatura"), ("hr", "humedad"), ("vv", "viento"),
            ("prec", "lluvia"), ("pres", "presion"), ("dir", "direccion_viento")
        ]
        
        for key_aemet, key_output in variables:
            valor_raw = estacion.get(key_aemet)
            es_valido, valor = _validar_dato_meteorologico(key_aemet, valor_raw)
            datos_procesados[key_output] = valor if es_valido else None
        
        return datos_procesados

    def obtener_clima_por_coordenadas(self, lat: float, lon: float, 
                                  max_distancia: float = 50) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos meteorológicos para unas coordenadas.
        
        Args:
            lat: Latitud
            lon: Longitud
            max_distancia: Distancia máxima a la estación (km). Default 50km
        
        Returns:
            Dict con datos meteorológicos o None si falla todo
        """
        self.logger.info(f"Solicitando clima para: {lat}, {lon}")
        
        # Obtener datos de AEMET
        observaciones = self._obtener_datos_crudos()
        
        if not observaciones:
            self.logger.warning("No hay datos de AEMET")
            return self._generar_fallback(lat, lon)
        
        # Buscar estación cercana
        estacion, distancia = self._buscar_estacion_cercana(lat, lon, observaciones, max_distancia)
        
        if not estacion:
            # Intentar con mayor distancia
            self.logger.info("Intentando con mayorradio de búsqueda")
            estacion, distancia = self._buscar_estacion_cercana(lat, lon, observaciones, 100)
            
            if not estacion:
                return self._generar_fallback(lat, lon)
        
        # Procesar datos
        datos = self._procesar_estacion(estacion)
        datos["_metadata"] = {
            "estacion_distancia_km": round(distancia, 2),
            "estacion_nombre": estacion.get("ubi"),
            "fuente": "AEMET",
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"Estación encontrada: {estacion.get('ubi')} a {distancia:.1f}km")
        
        return datos

    def _generar_fallback(self, lat: float, lon: float, estacion=None) -> Dict[str, Any]:
        """Genera datos de fallback cuando AEMET falla."""
        from services.geolocation_service import reverse_geocode
        
        # Intentar reverse geocoding
        city_info = None
        try:
            city_info = reverse_geocode(lat, lon)
        except Exception:
            pass
        
        return {
            "estacion_id": "FALLBACK",
            "ubi": city_info.get("ciudad", "Ubicación desconocida") if city_info else "Fallback",
            "lat": lat,
            "lon": lon,
            "temperatura": None,  # Sin datos reales
            "humedad": None,
            "viento": None,
            "lluvia": None,
            "presion": None,
            "_fallback": True,
            "_error": "Sin datos de AEMET disponibles",
            "_ciudad": city_info.get("ciudad") if city_info else None,
            "_provincia": city_info.get("provincia") if city_info else None,
            "timestamp": datetime.now().isoformat()
        }

    def obtener_clima_por_municipio(self, municipio: str) -> Optional[Dict]:
        """Obtiene clima por nombre de municipio."""
        from services.geolocation_service import geocode_city
        
        # Geocodificar
        location = geocode_city(municipio)
        if not location:
            return None
        
        return self.obtener_clima_por_coordenadas(
            location["lat"], 
            location["lon"]
        )


# ==== Funciones públicas para uso en app.py =====

def obtener_clima_por_coordenadas(lat: float, lon: float, use_cache: bool = True) -> Optional[Dict]:
    """Función puente para obtener clima por coordenadas."""
    timeout = int(os.getenv("AEMET_TIMEOUT", "20"))
    service = WeatherAPIService(timeout=timeout, use_cache=use_cache)
    return service.obtener_clima_por_coordenadas(lat, lon)


def obtener_clima_por_municipio(municipio: str) -> Optional[Dict]:
    """Función puente para obtener clima por municipio."""
    service = WeatherAPIService()
    return service.obtener_clima_por_municipio(municipio)