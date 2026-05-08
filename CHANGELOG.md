# CHANGELOG - ClimApp-Analytics-Pro

Todos los cambios notables de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [2.1.0] - 2026-05-08

### Agregado
- **Rate Limiter** - Protección contra abuso:
  - 30 req/min para /api/clima
  - 10 req/min para /api/geo
  - 100 req/min por defecto
- **Validación de datos meteorológicos** - Rangos válidos según OMM
- **Mejora en búsqueda de estación** - Hasta 100km si es necesario

### Modificado
- weather_api_service.py con validaciones estrictas
- app.py con rate limiting

## [2.0.0] - 2026-05-08

### Agregado
- **GeolocationService** - Servicio de geolocalización basado en fuentes oficiales:
  - IP-API.com para geolocalización por IP
  - Nominatim (OpenStreetMap) para geocoding y reverse geocoding
  - Caché automático para evitar repeated calls
- **AlertService actualizado** - Ahora lee umbrales desde config/alertas.json:
  - 6 niveles de alerta para temperatura (extremo, alto, medio)
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
- Sistema inicial de clima con Flask
- Integración con AEMET OpenData
- Fallback básico por ciudades
- Sistema de caché offline
- Tests con pytest
- Modelo MVC (CSR)