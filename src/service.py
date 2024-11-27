import asyncio
import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse
from config import STATIC_PATH, CHUNK_SIZE
from models import FileModel
from utils import upload_file_to_storage


def get_file_path(file: FileModel):
    return f"{STATIC_PATH}/{file.id}{file.extension}"


async def load_file_info(s: AsyncSession, id: uuid.UUID) -> FileModel:
    file = await s.execute(select(FileModel).filter(FileModel.id == id).limit(1))
    file = file.scalar()
    if not file:
        raise HTTPException(404, f'File not found')
    return file


async def get_file_response(s: AsyncSession, id: uuid.UUID) -> FileResponse:
    file = await load_file_info(s, id)
    if not os.path.exists(get_file_path(file)):
        raise HTTPException(404, 'File not found')
    return FileResponse(
        path=get_file_path(file),
        filename=file.name + file.extension,
        media_type=file.format
    )


async def save_file(s: AsyncSession, upload_file: UploadFile) -> FileModel:
    name, extension = os.path.splitext(upload_file.filename)
    file = FileModel(name=name, format=upload_file.content_type, extension=extension, size=upload_file.size)
    s.add(file)
    await s.commit()
    await s.refresh(file)

    # Streaming file into static folder
    async with aiofiles.open(get_file_path(file), mode='wb+') as f:
        while chunk := await upload_file.read(CHUNK_SIZE):
            await f.write(chunk)

    # Running task: upload file to s3
    asyncio.create_task(upload_file_to_storage(f'{file.id}{file.extension}'))
    return file
