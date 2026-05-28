from fastapi import APIRouter

from app.api.v1 import domains, evidence, health, imports, learner, review, sessions, skills, tutor

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(domains.router, prefix="/domains", tags=["domains"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(learner.router, prefix="/learner", tags=["learner"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(tutor.router, prefix="/tutor", tags=["tutor"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
