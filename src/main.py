import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import create_db_and_tables, get_async_session
from schemas import FileSchema
from service import save_file, get_file_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.post('/upload_file', response_model=FileSchema)
async def post_upload_file(file: UploadFile, s: AsyncSession = Depends(get_async_session)):
    return await save_file(s, file)


@app.get('/file/{id}')
async def get_file(id: uuid.UUID, s: AsyncSession = Depends(get_async_session)):
    return await get_file_info(s, id)