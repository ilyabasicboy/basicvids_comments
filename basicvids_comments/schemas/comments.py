from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Comment(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    video_id: str = Field(index=True, max_length=100)
    parent_id: str | None = Field(default=None, index=True, max_length=100)
    text: str = Field(max_length=2000)
    author_id: int = Field(index=True)
    author_username: str | None = Field(default=None, max_length=100)
    author_first_name: str | None = Field(default=None, max_length=100)
    author_last_name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=utc_now,
        nullable=False,
    )
    updated_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=utc_now,
        nullable=False,
    )
