from sqlalchemy import select
from sqlalchemy.orm import Session

from models.core import Property


def get_property(session: Session, parcel_id: str) -> Property | None:
    return session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
