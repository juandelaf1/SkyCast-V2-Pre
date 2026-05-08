import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

ALERTAS_CONFIG = Path("config/alertas.json")

_alertas_config = None


def _load_alertas_config() -> Dict:
    """Carga configuración de alertas desde JSON."""
    global _alertas_config
    if _alertas_config is not None:
        return _alertas_config
    
    if ALERTAS_CONFIG.exists():
        try:
            with open(ALERTAS_CONFIG, "r", encoding="utf-8") as f:
                _alertas_config = json.load(f)
            logger.info("Configuración de alertas cargada desde config/alertas.json")
            return _alertas_config
        except Exception as e:
            logger.error(f"Error cargando alertas config: {e}")
    
    _alertas_config = _get_default_config()
    return _alertas_config


def _get_default_config() -> Dict:
    """Configuración por defecto si no existe el archivo."""
    return {
        "alertas": {
            "temperatura": {
                "roja_alta": {"valor": 40, "descripcion": "Extremo", "color": "#dc2626"},
                "naranja_alta": {"valor": 35, "descripcion": "Muy alto", "color": "#f97316"},
                "naranja_baja": {"valor": 0, "descripcion": "Helada", "color": "#f97316"}
            },
            "viento": {"roja": {"valor": 80, "descripcion": "Extremo", "color": "#dc2626"}},
            "lluvia": {"roja": {"valor": 60, "descripcion": "Extremo", "color": "#dc2626"}},
            "humedad": {"naranja": {"valor": 95, "descripcion": "Extremo", "color": "#f97316"}}
        }
    }


class AlertService:
    """
    Servicio de alertas basado en configuración JSON.
    No hardcodeado - los umbrales se leen desde config/alertas.json
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or _load_alertas_config()
        self.alertas_config = self.config.get("alertas", {})
    
    def evaluar_alertas(self, registro: Dict[str, Any]) -> List[Dict]:
        """
        Evalúa un registro y genera alertas basadas en configuración.
        Devuelve lista de alertas con toda la información.
        """
        if not registro or not isinstance(registro, dict):
            return []
        
        if "temperatura" not in registro:
            return []
        
        alertas = []
        
        try:
            temp = float(registro.get("temperatura", 0))
            viento = float(registro.get("viento", 0))
            lluvia = float(registro.get("lluvia", 0))
            humedad = float(registro.get("humedad", 0))
        except (TypeError, ValueError):
            return []
        
        # Temperatura
        alertas.extend(self._evaluar_parametro("temperatura", temp))
        
        # Viento
        alertas.extend(self._evaluar_parametro("viento", viento))
        
        # Lluvia
        alertas.extend(self._evaluar_parametro("lluvia", lluvia))
        
        # Humedad
        alertas.extend(self._evaluar_parametro("humedad", humedad))
        
        return alertas
    
    def _evaluar_parametro(self, parametro: str, valor: float) -> List[Dict]:
        """Evalúa un parámetro específico."""
        alertas = []
        config_param = self.alertas_config.get(parametro, {})
        
        if not config_param:
            return []
        
        for nivel, regla in config_param.items():
            umbral = regla.get("valor")
            if umbral is None:
                continue
            
            es_alerta = False
            if nivel.endswith("_baja") or nivel == "naranja_baja":
                es_alerta = valor <= umbral
            else:
                es_alerta = valor >= umbral
            
            if es_alerta:
                alertas.append({
                    "parametro": parametro,
                    "tipo": nivel,
                    "valor": valor,
                    "umbral": umbral,
                    "descripcion": regla.get("descripcion"),
                    "color": regla.get("color"),
                    "icono": regla.get("icono"),
                    "nivel": regla.get("nivel", nivel)
                })
        
        return alertas
    
    def get_alertas_activas(self, registro: Dict[str, Any]) -> List[str]:
        """Devuelve solo los nombres de las alertas activas."""
        alertas = self.evaluar_alertas(registro)
        return [a["tipo"] for a in alertas]
    
    def tiene_alerta(self, registro: Dict[str, Any], nivel: str = None) -> bool:
        """Check si el registro tiene alerta de cierto nivel."""
        alertas = self.evaluar_alertas(registro)
        if not nivel:
            return len(alertas) > 0
        return any(a.get("nivel") == nivel for a in alertas)
    
    def get_nivel_maximo(self, registro: Dict[str, Any]) -> str:
        """Devuelve el nivel máximo de alerta (extremo > alto > medio)."""
        alertas = self.evaluar_alertas(registro)
        if not alertas:
            return "normal"
        
        niveles = {"extremo": 3, "alto": 2, "medio": 1}
        max_nivel = max(alertas, key=lambda x: niveles.get(x.get("nivel", 0), 0))
        return max_nivel.get("nivel", "normal")
    
    def get_summary(self, registro: Dict[str, Any]) -> Dict:
        """Resumen completo del estado de alertas."""
        alertas = self.evaluar_alertas(registro)
        return {
            "has_alerts": len(alertas) > 0,
            "count": len(alertas),
            "nivel_max": self.get_nivel_maximo(registro),
            "alerts": alertas
        }


_alert_service = None


def get_alert_service() -> AlertService:
    """Obtiene instancia singleton del servicio de alertas."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service


def reload_alert_config() -> None:
    """Recarga la configuración de alertas."""
    global _alertas_config, _alert_service
    _alertas_config = None
    _alert_service = None