import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any

class StructuredLogger:
    """Structured JSON logging and basic metrics framework."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: str, event: str, **kwargs):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))

    def info(self, event: str, **kwargs):
        self._log("INFO", event, **kwargs)

    def error(self, event: str, **kwargs):
        self._log("ERROR", event, **kwargs)

    def warn(self, event: str, **kwargs):
        self._log("WARN", event, **kwargs)
        
    def metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Logs a metric for Prometheus/Datadog scraping."""
        self._log("METRIC", "metric_recorded", metric_name=metric_name, value=value, tags=tags or {})

# Global logger instance
logger = StructuredLogger("rescuenet_core")
