from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from basicvids_comments.schemas.comments import Comment
from basicvids_comments.settings import settings


engine = create_engine(settings.DATABASE_URL)


def create_db_and_tables():
    settings.DATA_PATH.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    ensure_comment_parent_id_column()


def ensure_comment_parent_id_column():
    inspector = inspect(engine)
    if "comment" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("comment")}
    if "parent_id" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE comment ADD COLUMN parent_id VARCHAR(100)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_comment_parent_id ON comment (parent_id)"))


async def get_session():
    with Session(engine) as session:
        yield session
