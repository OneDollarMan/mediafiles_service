import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse
from db import create_db_and_tables, get_async_session
from schemas import FileSchema
from service import save_file, load_file_info, get_file_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.post('/upload_file', response_model=FileSchema)
async def post_upload_file(file: UploadFile, s: AsyncSession = Depends(get_async_session)):
    return await save_file(s, file)


@app.get('/file/{id}', response_model=FileSchema)
async def get_file_info(id: uuid.UUID, s: AsyncSession = Depends(get_async_session)):
    return await load_file_info(s, id)


@app.get('/file/{id}/download', response_class=FileResponse)
async def get_download_file(id: uuid.UUID, s: AsyncSession = Depends(get_async_session)):
    return await get_file_response(s, id)