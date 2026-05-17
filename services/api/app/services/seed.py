import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import DomainPack, SkillEdge, SkillNode


ROOT_DIR = Path(__file__).resolve().parents[4]
DOMAIN_PACKS_DIR = ROOT_DIR / "domain_packs"


def seed_domain_packs() -> None:
    for manifest_path in DOMAIN_PACKS_DIR.glob("*/domain.json"):
        seed_domain_pack(manifest_path)


def seed_domain_pack(manifest_path: Path) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        domain = db.scalar(select(DomainPack).where(DomainPack.slug == payload["slug"]))
        if domain is None:
            domain = DomainPack(
                slug=payload["slug"],
                name=payload["name"],
                version=payload["version"],
                description=payload.get("description", ""),
            )
            db.add(domain)
            db.flush()
        else:
            domain.name = payload["name"]
            domain.version = payload["version"]
            domain.description = payload.get("description", "")

        skill_by_slug: dict[str, SkillNode] = {}
        for index, item in enumerate(payload.get("skills", [])):
            skill = db.scalar(
                select(SkillNode).where(
                    SkillNode.domain_id == domain.id,
                    SkillNode.slug == item["slug"],
                )
            )
            if skill is None:
                skill = SkillNode(domain_id=domain.id, slug=item["slug"])
                db.add(skill)
            skill.title = item["title"]
            skill.summary = item.get("summary", "")
            skill.kind = item.get("kind", "concept")
            skill.difficulty = item.get("difficulty", 1)
            skill.estimated_minutes = item.get("estimated_minutes", 5)
            skill.content = item.get("content", "")
            skill.order_index = item.get("order_index", index)
            skill_by_slug[item["slug"]] = skill

        db.flush()

        for item in payload.get("skills", []):
            skill = skill_by_slug[item["slug"]]
            for prereq_slug in item.get("prerequisites", []):
                prereq = skill_by_slug.get(prereq_slug)
                if prereq is None:
                    continue
                edge = db.scalar(
                    select(SkillEdge).where(
                        SkillEdge.prerequisite_skill_id == prereq.id,
                        SkillEdge.skill_id == skill.id,
                        SkillEdge.relation_type == "prerequisite",
                    )
                )
                if edge is None:
                    db.add(
                        SkillEdge(
                            domain_id=domain.id,
                            prerequisite_skill_id=prereq.id,
                            skill_id=skill.id,
                        )
                    )
        db.commit()

