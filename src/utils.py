from contextlib import asynccontextmanager
from typing import AsyncIterator
import aioboto3
import aiofiles
from botocore.client import BaseClient
from config import CHUNK_SIZE, S3_BUCKET_NAME, S3_URL, STATIC_PATH, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, \
    AWS_REGION_NAME


@asynccontextmanager
async def get_s3_client() -> AsyncIterator[BaseClient]:
    session = aioboto3.Session()
    async with session.client(
            's3',
            endpoint_url=S3_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME
    ) as client:
        yield client


async def start_multipart_load(s3_client: BaseClient, filename: str) -> int:
    existing_buckets = await s3_client.list_buckets()
    if not any(bucket["Name"] == S3_BUCKET_NAME for bucket in existing_buckets["Buckets"]):
        await s3_client.create_bucket(Bucket=S3_BUCKET_NAME)

    multipart_upload = await s3_client.create_multipart_upload(
        Bucket=S3_BUCKET_NAME,
        Key=filename
    )
    return multipart_upload['UploadId']


async def finalize_multipart_load(
        s3_client: BaseClient,
        filename: str,
        upload_id: int,
        parts: list[dict]
):
    await s3_client.complete_multipart_upload(
        Bucket=S3_BUCKET_NAME,
        Key=filename,
        UploadId=upload_id,
        MultipartUpload={'Parts': parts}
    )


async def upload_file_to_storage(filename: str):
    """Streaming file to s3-like storage"""
    async with get_s3_client() as s3_client:
        upload_id = await start_multipart_load(s3_client, filename)

        parts = []
        part_number = 1

        async with aiofiles.open(f'{STATIC_PATH}/{filename}', mode="rb") as file:
            while chunk := await file.read(CHUNK_SIZE):
                part = await s3_client.upload_part(
                    Bucket=S3_BUCKET_NAME,
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

        await finalize_multipart_load(s3_client, filename, upload_id, parts)
