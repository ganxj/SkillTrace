from sqlalchemy import inspect, text

from app.db.session import Base, engine


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "skill_nodes" not in inspector.get_table_names():
        return

    skill_columns = {column["name"] for column in inspector.get_columns("skill_nodes")}
    skill_additions = {
        "lesson_explain": "TEXT DEFAULT ''",
        "key_points_json": "TEXT DEFAULT '[]'",
        "questions_json": "TEXT DEFAULT '[]'",
    }
    with engine.begin() as conn:
        for name, ddl in skill_additions.items():
            if name not in skill_columns:
                conn.execute(text(f"ALTER TABLE skill_nodes ADD COLUMN {name} {ddl}"))

        if "content_imports" in inspector.get_table_names():
            import_columns = {column["name"] for column in inspector.get_columns("content_imports")}
            import_additions = {
                "total_segments": "INTEGER DEFAULT 0",
                "processed_segments": "INTEGER DEFAULT 0",
                "current_step": "VARCHAR(260) DEFAULT ''",
            }
            for name, ddl in import_additions.items():
                if name not in import_columns:
                    conn.execute(text(f"ALTER TABLE content_imports ADD COLUMN {name} {ddl}"))
