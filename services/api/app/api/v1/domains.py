from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DomainPack
from app.schemas import DomainPackRead

router = APIRouter()


@router.get("", response_model=list[DomainPackRead])
def list_domains(db: Session = Depends(get_db)) -> list[DomainPack]:
    return list(db.scalars(select(DomainPack).order_by(DomainPack.created_at)).all())

