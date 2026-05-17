from fastapi import Header

from app.core.config import settings


def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    return x_user_id or settings.demo_user_id

