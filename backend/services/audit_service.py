from sqlalchemy.orm import Session

from models.core import AuditLog


def record_audit(session: Session, action: str, entity_type: str, entity_id: str, **details) -> None:
    session.add(AuditLog(action=action, entity_type=entity_type, entity_id=entity_id, **details))
