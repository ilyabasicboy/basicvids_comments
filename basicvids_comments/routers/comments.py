from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from basicvids_comments.auth import CurrentUser, get_current_user
from basicvids_comments.db import get_session
from basicvids_comments.models.comments import CommentChange, CommentCreate, CommentDeleteResponse, CommentList, CommentPublic
from basicvids_comments.schemas.comments import Comment


router = APIRouter(tags=["Comments"], prefix="/comments")


def ensure_can_modify(comment: Comment, current_user: CurrentUser) -> None:
    if comment.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author or an admin can change this comment")


@router.post("/", response_model=CommentPublic, status_code=201)
async def create_comment(
    data: CommentCreate,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> Comment:
    comment = Comment(
        video_id=data.video_id,
        text=data.text.strip(),
        author_id=current_user.id,
        author_username=current_user.username,
        author_first_name=current_user.first_name,
        author_last_name=current_user.last_name,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.get("/", response_model=CommentList)
async def list_comments(
    video_id: str | None = None,
    offset: int = 0,
    limit: int = Query(default=20, le=100),
    session: Session = Depends(get_session),
) -> CommentList:
    statement = select(Comment)
    if video_id:
        statement = statement.where(Comment.video_id == video_id)

    statement = statement.order_by(col(Comment.created_at).desc()).offset(offset).limit(limit)
    comments = session.exec(statement).all()
    return CommentList(
        comments=[CommentPublic.model_validate(comment) for comment in comments],
        count=len(comments),
    )


@router.get("/{comment_id}", response_model=CommentPublic)
async def get_comment(
    comment_id: str,
    session: Session = Depends(get_session),
) -> Comment:
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.patch("/{comment_id}", response_model=CommentPublic)
async def change_comment(
    comment_id: str,
    data: CommentChange,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> Comment:
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    ensure_can_modify(comment, current_user)

    comment.text = data.text.strip()
    comment.updated_at = datetime.now(timezone.utc)
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.delete("/{comment_id}", response_model=CommentDeleteResponse, status_code=200)
async def delete_comment(
    comment_id: str,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> CommentDeleteResponse:
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    ensure_can_modify(comment, current_user)

    session.delete(comment)
    session.commit()
    return CommentDeleteResponse(message="Comment deleted successfully")
