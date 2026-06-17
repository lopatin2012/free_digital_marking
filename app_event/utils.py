# app_event/utils.py

from app_event.models import EventLog

def log_event(module, level, message, actor='system', metadata=None):
    EventLog.objects.create(
        module=module,
        level=level,
        message=message,
        actor=actor,
        metadata=metadata or {}
    )
