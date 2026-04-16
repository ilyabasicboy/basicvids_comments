from sqlmodel import Session, delete
import httpx
import pytest

from basicvids_comments.auth import CurrentUser, get_current_user
from basicvids_comments.models.comments import CommentPublic
from basicvids_comments.schemas.comments import Comment
from basicvids_comments.tests import app, engine


pytestmark = pytest.mark.anyio


async def request(method: str, url: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


def user(user_id: int = 1, is_admin: bool = False) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        username=f"user-{user_id}",
        first_name="Test",
        last_name="Author",
        email=f"user-{user_id}@example.com",
        is_admin=is_admin,
        email_confirmed=True,
    )


def set_current_user(current_user: CurrentUser) -> None:
    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_current_user] = override_get_current_user


class BaseTestComments:
    def setup_method(self):
        set_current_user(user())
        with Session(engine) as session:
            session.exec(delete(Comment))
            session.commit()


class TestComments(BaseTestComments):
    method_url = "/api/v1/comments"

    async def create_comment(self, video_id: str = "video-1"):
        response = await request(
            "POST",
            f"{self.method_url}/",
            json={
                "video_id": video_id,
                "text": "First comment",
            },
        )
        return response.json()

    async def test_create_comment_success(self):
        response = await request(
            "POST",
            f"{self.method_url}/",
            json={
                "video_id": "video-1",
                "text": "First comment",
            },
        )

        assert response.status_code == 201
        response_data = response.json()
        assert CommentPublic(**response_data)
        assert response_data["video_id"] == "video-1"
        assert response_data["text"] == "First comment"
        assert response_data["author_id"] == 1
        assert response_data["author_username"] == "user-1"
        assert response_data["author_first_name"] == "Test"
        assert response_data["author_last_name"] == "Author"

    async def test_create_comment_unauthorized(self):
        app.dependency_overrides.pop(get_current_user, None)
        response = await request(
            "POST",
            f"{self.method_url}/",
            json={
                "video_id": "video-1",
                "text": "First comment",
            },
        )

        assert response.status_code == 401

    async def test_list_comments_success(self):
        await self.create_comment(video_id="video-1")
        await self.create_comment(video_id="video-2")

        response = await request("GET", f"{self.method_url}/", params={"video_id": "video-1"})

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert response_data["comments"][0]["video_id"] == "video-1"

    async def test_get_comment_success(self):
        comment = await self.create_comment()

        response = await request("GET", f"{self.method_url}/{comment['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == comment["id"]

    async def test_change_comment_success(self):
        comment = await self.create_comment()

        response = await request(
            "PATCH",
            f"{self.method_url}/{comment['id']}",
            json={"text": "Changed comment"},
        )

        assert response.status_code == 200
        assert response.json()["text"] == "Changed comment"

    async def test_change_comment_forbidden_for_non_author(self):
        comment = await self.create_comment()
        set_current_user(user(user_id=2))

        response = await request(
            "PATCH",
            f"{self.method_url}/{comment['id']}",
            json={"text": "Changed comment"},
        )

        assert response.status_code == 403

    async def test_change_comment_success_for_admin(self):
        comment = await self.create_comment()
        set_current_user(user(user_id=2, is_admin=True))

        response = await request(
            "PATCH",
            f"{self.method_url}/{comment['id']}",
            json={"text": "Changed comment"},
        )

        assert response.status_code == 200

    async def test_delete_comment_success(self):
        comment = await self.create_comment()

        response = await request("DELETE", f"{self.method_url}/{comment['id']}")

        assert response.status_code == 200
        assert response.json() == {"message": "Comment deleted successfully"}

        response = await request("GET", f"{self.method_url}/{comment['id']}")
        assert response.status_code == 404

    async def test_delete_comment_forbidden_for_non_author(self):
        comment = await self.create_comment()
        set_current_user(user(user_id=2))

        response = await request("DELETE", f"{self.method_url}/{comment['id']}")

        assert response.status_code == 403

    async def test_delete_comment_not_found(self):
        response = await request("DELETE", f"{self.method_url}/missing-comment")

        assert response.status_code == 404
