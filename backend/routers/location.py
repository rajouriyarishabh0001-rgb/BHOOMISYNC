from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.session import get_db
from models.core import User, UserLocation
from schemas.location import LocationCreate, LocationResponse
from security import current_user

router = APIRouter(prefix="/api/location", tags=["location"])


@router.post("", response_model=LocationResponse, status_code=201)
def save_location(request: LocationCreate, user: Annotated[User, Depends(current_user)], session: Annotated[Session, Depends(get_db)]) -> LocationResponse:
    location = UserLocation(user_id=user.id, latitude=request.latitude, longitude=request.longitude, accuracy=request.accuracy, source=request.source)
    session.add(location); session.commit(); session.refresh(location)
    return LocationResponse(id=location.id, **request.model_dump())


@router.delete("/history", status_code=204)
def delete_location_history(user: Annotated[User, Depends(current_user)], session: Annotated[Session, Depends(get_db)]) -> None:
    session.execute(delete(UserLocation).where(UserLocation.user_id == user.id)); session.commit()