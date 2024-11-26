import asyncio
import os
import uuid
from http.client import HTTPException

import aioboto3
import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config import STATIC_PATH, CHUNK_SIZE
from models import FileModel


async def get_file_info(s: AsyncSession, id: uuid.UUID):
    file = await s.execute(select(FileModel).filter(FileModel.id == id).limit(1))
    file = file.scalar()
    if not file:
        raise HTTPException(404, f'File with {id=} not found')

    return file


async def save_file(s: AsyncSession, upload_file: UploadFile) -> FileModel:
    name, extension = os.path.splitext(upload_file.filename)
    file = FileModel(name=name, format=upload_file.content_type, extension=extension, size=upload_file.size)
    s.add(file)
    await s.commit()
    await s.refresh(file)


    file_path = f"{STATIC_PATH}/{file.id}{file.extension}"
    async with aiofiles.open(file_path, mode='wb+') as f:
        while chunk := await upload_file.read(CHUNK_SIZE):
            await f.write(chunk)

    asyncio.create_task(upload_file_to_storage(upload_file, 'test', f'{file.id}{file.extension}'))
    return file


async def upload_file_to_storage(
        file: UploadFile,
        bucket_name: str,
        filename: str
):
    """
    Асинхронная функция загрузки файла в облачное хранилище потоком

    :param file: Файл от FastAPI
    :param bucket_name: Имя bucket в хранилище
    :param filename: Полное название файла
    """
    try:
        session = aioboto3.Session()

        # Асинхронная загрузка потоком
        async with session.client('s3') as s3_client:
            # Начинаем загрузку мультипарт
            multipart_upload = await s3_client.create_multipart_upload(
                Bucket=bucket_name,
                Key=filename
            )
            upload_id = multipart_upload['UploadId']

            # Список загруженных частей
            parts = []
            part_number = 1

            # Читаем файл chunks и загружаем части
            while chunk := await file.read(CHUNK_SIZE):
                part = await s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=filename,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )

                parts.append({
                    'PartNumber': part_number,
                    'ETag': part['ETag']
                })

                part_number += 1

            # Финализируем мультипарт загрузку
            await s3_client.complete_multipart_upload(
                Bucket=bucket_name,
                Key=filename,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )

        print({
            "success": True,
            "filename": filename,
            "bucket": bucket_name
        })

    except Exception as e:
        print({
            "success": False,
            "error": str(e)
        })
    finally:
        await file.close()