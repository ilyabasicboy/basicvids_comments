from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlmodel import Session, col, select

from basicvids_comments.auth import CurrentUser, get_current_user
from basicvids_comments.db import get_session
from basicvids_comments.models.comments import CommentChange, CommentCreate, CommentDeleteResponse, CommentList, CommentPublic
from basicvids_comments.rate_limit import client_identifier, enforce_rate_limit
from basicvids_comments.schemas.comments import Comment


router = APIRouter(tags=["Comments"], prefix="/comments")


def ensure_can_modify(comment: Comment, current_user: CurrentUser) -> None:
    if comment.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author or an admin can change this comment")


def get_parent_comment_or_400(session: Session, parent_id: str | None, video_id: str) -> Comment | None:
    if not parent_id:
        return None

    parent = session.get(Comment, parent_id)
    if not parent or parent.video_id != video_id:
        raise HTTPException(status_code=400, detail="Parent comment not found for this video")
    if parent.parent_id:
        raise HTTPException(status_code=400, detail="Replies can only be added to top-level comments")

    return parent


@router.post("/", response_model=CommentPublic, status_code=201)
async def create_comment(
    data: CommentCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> Comment:
    await enforce_rate_limit("create_comment_ip", client_identifier(request), 30, 60)
    await enforce_rate_limit("create_comment_user", f"user:{current_user.id}", 10, 60)
    get_parent_comment_or_400(session, data.parent_id, data.video_id)
    comment = Comment(
        video_id=data.video_id,
        parent_id=data.parent_id,
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
    count_statement = select(func.count()).select_from(Comment)
    if video_id:
        statement = statement.where(Comment.video_id == video_id, Comment.parent_id == None)  # noqa: E711
        count_statement = count_statement.where(Comment.video_id == video_id, Comment.parent_id == None)  # noqa: E711

    statement = statement.order_by(col(Comment.created_at).desc()).offset(offset).limit(limit)
    comments = session.exec(statement).all()
    total_count = session.exec(count_statement).one()
    if video_id and comments:
        parent_ids = [comment.id for comment in comments]
        replies = session.exec(
            select(Comment)
            .where(col(Comment.parent_id).in_(parent_ids))
            .order_by(col(Comment.created_at).asc())
        ).all()
        comments = [*comments, *replies]
    return CommentList(
        comments=[CommentPublic.model_validate(comment) for comment in comments],
        count=total_count,
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
    request: Request,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> Comment:
    await enforce_rate_limit("change_comment_user", f"user:{current_user.id}", 20, 60)
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
    request: Request,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> CommentDeleteResponse:
    await enforce_rate_limit("delete_comment_user", f"user:{current_user.id}", 30, 60)
    comment = session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    ensure_can_modify(comment, current_user)

    replies = session.exec(select(Comment).where(Comment.parent_id == comment.id)).all()
    for reply in replies:
        session.delete(reply)
    session.delete(comment)
    session.commit()
    return CommentDeleteResponse(message="Comment deleted successfully")
