from sqlalchemy import inspect, text

from app.db.session import Base, engine


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "skill_nodes" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("skill_nodes")}
    additions = {
        "lesson_explain": "TEXT DEFAULT ''",
        "key_points_json": "TEXT DEFAULT '[]'",
        "questions_json": "TEXT DEFAULT '[]'",
    }
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE skill_nodes ADD COLUMN {name} {ddl}"))
