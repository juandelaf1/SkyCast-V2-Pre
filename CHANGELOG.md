# CHANGELOG - ClimApp-Analytics-Pro

Todos los cambios notables de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [2.0.0] - 2026-05-08

### Agregado
- **GeolocationService** - Servicio de geolocalización basado en fuentes oficiales:
  - IP-API.com para geolocalización por IP
  - Nominatim (OpenStreetMap) para geocoding y reverse geocoding
  - Caché automático para evitar重复 llamadas
- **AlertService actualizado** - Ahora lee umbrales desde config/alertas.json:
  - 6 niveles de alerta para temperatura (roja_extrema, roja, naranja, amarillo_alta, amarillo_baja)
  - 3 niveles para viento y lluvia
  - 2 niveles para humedad
- **Nuevos endpoints API**:
  - `/api/clima/<ciudad>` - Obtener clima por nombre de ciudad
  - `/api/geo/<ciudad>` - Geocodificar ciudad
  - `/api/health` - Health check
  - `/api/alertas` - Ver configuración de alertas

### Modificado
- weather_api_service.py con fallback avanzado
- app.py con nuevos endpoints

## [1.0.0] - 2026-05-07

### Agregado
- Sistema inicial de cuaca con Flask
- Integración con AEMET OpenData
- Fallback básico por ciudades
- Sistema de caché offline
- Tests con pytest
- Modelo MVC (CSR)