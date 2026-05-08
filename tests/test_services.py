import pytest
import os
from services.normalizer_service import normalizar_datos_aemet
from services.alert_service import AlertService
from services.location_resolver_service import resolve_location, get_available_cities, search_city


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


# ==== Alert Service Tests ====
def test_alert_service_red_alert():
    """Alerta ROJA a partir de 40 grados."""
    service = AlertService()
    data = {"temperatura": 42.0, "viento": 10.0, "lluvia": 0.0, "humedad": 40}
    alertas = service.evaluar_alertas(data)
    assert "ROJA" in alertas


def test_alert_service_orange_alert():
    """Alerta NARANJA a partir de 35 grados."""
    service = AlertService()
    data = {"temperatura": 36.0, "viento": 10.0, "lluvia": 0.0, "humedad": 40}
    alertas = service.evaluar_alertas(data)
    assert "NARANJA" in alertas


def test_alert_service_cold_alert():
    """Alerta HELADA a 0 grados o menos."""
    service = AlertService()
    data = {"temperatura": -1.0, "viento": 10.0, "lluvia": 0.0, "humedad": 40}
    alertas = service.evaluar_alertas(data)
    assert "HELADA" in alertas


def test_alert_service_multiple_alerts():
    """Alertas acumulativas."""
    service = AlertService()
    data = {"temperatura": 20.0, "viento": 80.0, "lluvia": 45.0, "humedad": 50}
    alertas = service.evaluar_alertas(data)
    assert "VIENTO_FUERTE" in alertas
    assert "LLUVIA_INTENSA" in alertas


def test_alert_service_high_humidity():
    """Alerta de humedad alta."""
    service = AlertService()
    data = {"temperatura": 25.0, "viento": 10.0, "lluvia": 0.0, "humedad": 95}
    alertas = service.evaluar_alertas(data)
    assert "HUMEDAD_ALTA" in alertas


def test_alert_service_no_alerts():
    """Sin alertas cuando valores normales."""
    service = AlertService()
    data = {"temperatura": 20.0, "viento": 10.0, "lluvia": 5.0, "humedad": 60}
    alertas = service.evaluar_alertas(data)
    assert len(alertas) == 0


def test_alert_service_empty_data():
    """Datos vacíos devuelve lista vacía."""
    service = AlertService()
    alertas = service.evaluar_alertas({})
    assert alertas == []


# ==== Location Resolver Tests ====
def test_resolve_location_by_gps():
    """Resolución por coordenadas GPS."""
    result = resolve_location(lat="40.4167", lon="-3.7033")
    assert result["success"] is True
    assert result["source"] == "GPS"
    assert result["lat"] == 40.4167


def test_resolve_location_by_city():
    """Resolución por nombre de ciudad."""
    result = resolve_location(city="Madrid")
    assert result["success"] is True
    assert result["source"] == "MANUAL"


def test_resolve_location_case_insensitive():
    """Búsqueda case-insensitive."""
    result = resolve_location(city="BARCELONA")
    assert result["success"] is True


def test_resolve_location_unknown_city():
    """Ciudad desconocida usa fallback."""
    result = resolve_location(city="CiudadInexistente")
    assert result["success"] is True
    assert result["source"] == "DEFAULT"


def test_resolve_location_no_params():
    """Sin parámetros usa fallback."""
    result = resolve_location()
    assert result["success"] is True
    assert result["source"] == "DEFAULT"


def test_get_available_cities():
    """Lista de ciudades disponibles."""
    cities = get_available_cities()
    assert "madrid" in cities
    assert "barcelona" in cities
    assert len(cities) >= 50


def test_search_city():
    """Búsqueda de ciudades."""
    results = search_city("bar")
    assert any("barcelona" in r for r in results)


# 18 tests passing