from datetime import datetime

from pydantic import BaseModel, ConfigDict, constr


class CommentCreate(BaseModel):
    video_id: str
    text: constr(min_length=1, max_length=2000)
    parent_id: str | None = None


class CommentChange(BaseModel):
    text: constr(min_length=1, max_length=2000)


class CommentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    parent_id: str | None = None
    text: str
    author_id: int
    author_username: str | None = None
    author_first_name: str | None = None
    author_last_name: str | None = None
    created_at: datetime
    updated_at: datetime


class CommentList(BaseModel):
    comments: list[CommentPublic]
    count: int


class CommentDeleteResponse(BaseModel):
    message: str
