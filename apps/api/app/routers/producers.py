from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import Producer
from app.routers.helpers import apply_update, commit_or_400, get_or_404
from app.schemas.common import ProducerCreate, ProducerRead, ProducerUpdate
from app.services.registry_service import RegistryService

router = APIRouter(prefix="/api/producers", tags=["producers"])


@router.get("", response_model=list[ProducerRead])
def list_producers(session: Session = Depends(get_session)) -> list[Producer]:
    return list(session.scalars(select(Producer).order_by(Producer.name_original)))


@router.post("", response_model=ProducerRead, status_code=201)
def create_producer(payload: ProducerCreate, session: Session = Depends(get_session)) -> Producer:
    producer = Producer(**payload.model_dump())
    RegistryService(session).apply_producer_fields(producer)
    session.add(producer)
    commit_or_400(session)
    session.refresh(producer)
    return producer


@router.get("/{producer_id}", response_model=ProducerRead)
def get_producer(producer_id: str, session: Session = Depends(get_session)) -> Producer:
    return get_or_404(session, Producer, producer_id, "Producer")


@router.patch("/{producer_id}", response_model=ProducerRead)
def update_producer(
    producer_id: str,
    payload: ProducerUpdate,
    session: Session = Depends(get_session),
) -> Producer:
    producer = get_or_404(session, Producer, producer_id, "Producer")
    apply_update(producer, payload.model_dump(exclude_unset=True))
    RegistryService(session).apply_producer_fields(producer)
    commit_or_400(session)
    session.refresh(producer)
    return producer
