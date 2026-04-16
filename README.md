# BasicVids Comments

Comments microservice for BasicVids.

## Stack

* Gunicorn
* FastAPI
* SQLModel
* SQLite by default

## Development

Use a virtual environment:

```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

Run tests:

```bash
pytest
```

Run locally:

```bash
uvicorn basicvids_comments.main:app --reload
```

## Container

```bash
mkdir -p data
docker compose up -d --build
```

## Configuration

| Variable              | Default                                           | Description                         |
| --------------------- | ------------------------------------------------- | ----------------------------------- |
| DATA_PATH             | ./data                                            | Data directory mounted in container |
| DATABASE_URL          | sqlite:///./data/database.db                      | Metadata database URL               |
| AUTH_CURRENT_USER_URL | http://basicvids_auth:8000/api/v1/users/detail/  | Auth service current-user endpoint  |

Project environment can be placed in:

```text
./data/.env
```

## API Documentation

### Health Check

- **GET** `/health`
  - **Response:** `{ "status": "ok" }`

### Comments

- **POST** `/api/v1/comments/`
  - **Requires:** authentication
  - **Body:** `{ "video_id": "video-id", "text": "Comment text" }`
  - **Response:** `{ id, video_id, text, author_id, author_username, author_first_name, author_last_name, created_at, updated_at }`

- **GET** `/api/v1/comments/`
  - **Query parameters:** `video_id` optional, `offset` default 0, `limit` default 20 max 100
  - **Response:** `{ comments: [...], count }`

- **GET** `/api/v1/comments/{comment_id}`
  - **Response:** `{ id, video_id, text, author_id, author_username, author_first_name, author_last_name, created_at, updated_at }`

- **PATCH** `/api/v1/comments/{comment_id}`
  - **Requires:** authentication as the comment author or an admin
  - **Body:** `{ "text": "Changed comment text" }`
  - **Response:** `{ id, video_id, text, author_id, author_username, author_first_name, author_last_name, created_at, updated_at }`

- **DELETE** `/api/v1/comments/{comment_id}`
  - **Requires:** authentication as the comment author or an admin
  - **Response:** `{ "message": "Comment deleted successfully" }`
