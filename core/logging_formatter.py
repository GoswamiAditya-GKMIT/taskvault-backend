import json
import logging
import datetime

class JSONFormatter(logging.Formatter):
    """
    Custom formatter to output logs in JSON format.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", "N/A"),
            "tenant_id": getattr(record, "tenant_id", "N/A"),
            "user_id": getattr(record, "user_id", "N/A"),
            "execution_time_ms": getattr(record, "execution_time_ms", "N/A"),
        }
        
        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)
