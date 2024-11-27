import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from botocore.client import BaseClient
from src.utils import get_s3_client, start_multipart_load, finalize_multipart_load, upload_file_to_storage
from src.config import S3_BUCKET_NAME, STATIC_PATH


@pytest.mark.asyncio
async def test_get_s3_client():
    async with get_s3_client() as s3_client:
        assert isinstance(s3_client, BaseClient)


@pytest.mark.asyncio
async def test_start_multipart_load():
    s3_client = AsyncMock()
    s3_client.list_buckets = AsyncMock(return_value={"Buckets": []})
    s3_client.create_multipart_upload = AsyncMock(return_value={"UploadId": "12345"})

    upload_id = await start_multipart_load(s3_client, "test_file.txt")

    s3_client.list_buckets.assert_called_once()
    s3_client.create_bucket.assert_called_once_with(Bucket=S3_BUCKET_NAME)
    s3_client.create_multipart_upload.assert_called_once_with(
        Bucket=S3_BUCKET_NAME, Key="test_file.txt"
    )
    assert upload_id == "12345"


@pytest.mark.asyncio
async def test_start_multipart_load_bucket_not_created():
    s3_client = AsyncMock()
    s3_client.list_buckets = AsyncMock(return_value={"Buckets": [{"Name": S3_BUCKET_NAME}]})

    await start_multipart_load(s3_client, "test_file.txt")

    s3_client.create_bucket.assert_not_called()



@pytest.mark.asyncio
async def test_finalize_multipart_load():
    s3_client = MagicMock()
    s3_client.complete_multipart_upload = AsyncMock(return_value={})

    parts = [{'PartNumber': 1, 'ETag': 'etag123'}]
    await finalize_multipart_load(s3_client, "test_file.txt", 12345, parts)

    s3_client.complete_multipart_upload.assert_called_once_with(
        Bucket=S3_BUCKET_NAME,
        Key="test_file.txt",
        UploadId=12345,
        MultipartUpload={"Parts": parts}
    )


@pytest.mark.asyncio
async def test_upload_file_to_storage():
    mock_upload_part = AsyncMock(return_value={"ETag": "etag123"})
    mock_finalize = AsyncMock()

    with patch("aiofiles.open", return_value=AsyncMock()) as mock_file, \
            patch("aioboto3.Session.client", return_value=AsyncMock()) as mock_client, \
            patch("src.utils.start_multipart_load", return_value=12345):
        mock_s3 = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_s3
        mock_s3.upload_part = mock_upload_part
        mock_s3.complete_multipart_upload = mock_finalize

        mock_file.return_value.__aenter__.return_value.read = AsyncMock(side_effect=[b'chunk1', b'chunk2', b''])

        await upload_file_to_storage("test_file.txt")

        mock_file.assert_called_once_with(f'{STATIC_PATH}/test_file.txt', mode="rb")
        mock_s3.upload_part.assert_any_call(
            Bucket=S3_BUCKET_NAME,
            Key="test_file.txt",
            PartNumber=1,
            UploadId=12345,
            Body=b'chunk1'
        )
        mock_s3.upload_part.assert_any_call(
            Bucket=S3_BUCKET_NAME,
            Key="test_file.txt",
            PartNumber=2,
            UploadId=12345,
            Body=b'chunk2'
        )

        mock_finalize.assert_called_once_with(
            Bucket=S3_BUCKET_NAME,
            Key="test_file.txt",
            UploadId=12345,
            MultipartUpload={'Parts': [{'PartNumber': 1, 'ETag': 'etag123'}, {'PartNumber': 2, 'ETag': 'etag123'}]}
        )


