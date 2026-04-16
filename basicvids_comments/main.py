from contextlib import asynccontextmanager

from fastapi import FastAPI

from basicvids_comments.db import create_db_and_tables
from basicvids_comments.routers.comments import router as comments_router
from basicvids_comments.routers.root import router as root_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="BasicVids Comments", lifespan=lifespan)

app.include_router(comments_router, prefix="/api/v1")
app.include_router(root_router)
