from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DomainPack
from app.schemas import DomainPackRead

router = APIRouter()


@router.get("", response_model=list[DomainPackRead])
def list_domains(db: Session = Depends(get_db)) -> list[DomainPack]:
    return list(db.scalars(select(DomainPack).order_by(DomainPack.created_at)).all())


@router.get("/latest", response_model=DomainPackRead)
def latest_domain(db: Session = Depends(get_db)) -> DomainPack:
    domain = db.scalar(select(DomainPack).order_by(desc(DomainPack.created_at)))
    if domain is None:
        raise HTTPException(status_code=404, detail="No domain packs found.")
    return domain
