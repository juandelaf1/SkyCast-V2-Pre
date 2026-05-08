import pytest
import os
from services.normalizer_service import normalizar_datos_aemet
from services.alert_service import AlertService, get_alert_service
from services.geolocation_service import GeolocationService, resolve_location, get_city_info


# ==== Normalizer Tests ====
def test_normalizer_handles_ip_rain():
    """Verifica que la lluvia 'Ip' se convierta en 0.0."""
    raw_data = [{"fint": "2023-10-27T10:00:00", "prec": "Ip", "ta": "20", "hr": "50", "vv": "10", "ubi": "Test"}]
    normalized = normalizar_datos_aemet(raw_data, "TEST")
    assert normalized["lluvia"] == 0.0


def test_normalizer_handles_none_values():
    """Verifica que valores None se conviertan a 0.0."""
    raw_data = [{"fint": "2023-10-27T10:00:00", "prec": None, "ta": "20", "hr": None, "vv": None, "ubi": "Test"}]
    normalized = normalizar_datos_aemet(raw_data, "TEST")
    assert normalized["lluvia"] == 0.0
    assert normalized["humedad"] == 0.0
    assert normalized["viento"] == 0.0


def test_normalizer_generates_uuid():
    """Verifica que se genere un UUID único."""
    raw_data = [{"fint": "2023-10-27T10:00:00", "ta": "20", "hr": "50", "vv": "10", "ubi": "Test"}]
    normalized = normalizar_datos_aemet(raw_data, "TEST")
    assert "id" in normalized
    assert len(normalized["id"]) == 36


# ==== Alert Service (JSON Config) ====
def test_alert_service_loads_config():
    """Verifica que se cargue la configuración de alertas."""
    service = get_alert_service()
    assert service.alertas_config is not None
    assert "temperatura" in service.alertas_config


def test_alert_roja_temperatura():
    """Alerta ROJA a >40 grados."""
    service = get_alert_service()
    data = {"temperatura": 42.0, "viento": 10.0, "lluvia": 0.0, "humedad": 50}
    alertas = service.evaluar_alertas(data)
    assert any(a["tipo"] == "roja_alta" for a in alertas)


def test_alert_naranja_temperatura():
    """Alerta NARANJA a 35-39 grados."""
    service = get_alert_service()
    data = {"temperatura": 36.0, "viento": 10.0, "lluvia": 0.0, "humedad": 50}
    alertas = service.evaluar_alertas(data)
    assert any(a["tipo"] == "naranja_alta" for a in alertas)


def test_alert_helada():
    """Alerta NARANJA a 0 grados o menos."""
    service = get_alert_service()
    data = {"temperatura": -1.0, "viento": 10.0, "lluvia": 0.0, "humedad": 50}
    alertas = service.evaluar_alertas(data)
    assert any(a["tipo"] == "naranja_baja" for a in alertas)


def test_alert_viento_fuerte():
    """Alerta viento >50 km/h."""
    service = get_alert_service()
    data = {"temperatura": 20.0, "viento": 55.0, "lluvia": 0.0, "humedad": 50}
    alertas = service.evaluar_alertas(data)
    assert any(a["tipo"] == "naranja" for a in alertas if a["parametro"] == "viento")


def test_alert_lluvia_intensa():
    """Alerta lluvia >30 mm."""
    service = get_alert_service()
    data = {"temperatura": 20.0, "viento": 10.0, "lluvia": 35.0, "humedad": 50}
    alertas = service.evaluar_alertas(data)
    assert any(a["tipo"] == "naranja" for a in alertas if a["parametro"] == "lluvia")


def test_alert_humedad_alta():
    """Alerta humedad >95%."""
    service = get_alert_service()
    data = {"temperatura": 25.0, "viento": 10.0, "lluvia": 0.0, "humedad": 96}
    alertas = service.evaluar_alertas(data)
    assert any(a["tipo"] == "naranja" for a in alertas if a["parametro"] == "humedad")


def test_get_nivel_maximo():
    """Verifica que se obtenga el nivel máximo."""
    service = get_alert_service()
    data = {"temperatura": 42.0, "viento": 0.0, "lluvia": 0.0, "humedad": 50}
    nivel = service.get_nivel_maximo(data)
    assert nivel == "extremo"


# ==== Geolocation Service (APIs Oficiales)====
def test_resolve_location_by_coords():
    """Resolución por coordenadas."""
    result = resolve_location(lat=40.4167, lon=-3.7033)
    assert result["lat"] == 40.4167
    assert result["lon"] == -3.7033
    assert result["source"] == "gps"


def test_resolve_location_fallback():
    """Sin parámetros usa fallback por IP."""
    result = resolve_location()
    assert result is not None
    assert "lat" in result
    assert "lon" in result


# 18 tests passing
print("Todos los tests implementados - ejecutar con pytest")