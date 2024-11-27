import asyncio
import uuid
from io import BytesIO
import pytest
from unittest.mock import AsyncMock, patch, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from src.service import load_file_info, get_file_response, save_file, get_file_path
from src.models import FileModel
from src.config import STATIC_PATH


class AsyncBytesIO:
    def __init__(self, initial_bytes):
        self._buffer = BytesIO(initial_bytes)

    async def read(self, size=-1):
        await asyncio.sleep(0)
        return self._buffer.read(size)


@pytest.mark.asyncio
async def test_load_file_info_success():
    # Mock AsyncSession and FileModel
    mock_session = AsyncMock(spec=AsyncSession)
    mock_file = FileModel(
        id=uuid.uuid4(),
        name='test_file',
        extension='.txt',
        format='text/plain'
    )

    # Configure the mock to return the file
    mock_execute = Mock()
    mock_execute.scalar.return_value = mock_file
    mock_session.execute.return_value = mock_execute

    # Test successful file info retrieval
    result = await load_file_info(mock_session, mock_file.id)

    # Verify the result matches the mock file
    assert result == mock_file
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_load_file_info_not_found():
    # Mock AsyncSession with no file found
    mock_session = AsyncMock(spec=AsyncSession)
    mock_execute = Mock()
    mock_execute.scalar.return_value = None
    mock_session.execute.return_value = mock_execute

    # Test file not found raises HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await load_file_info(mock_session, uuid.uuid4())

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_file_response_success(mocker):
    # Mock dependencies
    mock_session = AsyncMock(spec=AsyncSession)
    mock_file = FileModel(
        id=uuid.uuid4(),
        name='test_file',
        extension='.txt',
        format='text/plain'
    )

    # Mock load_file_info to return the file
    mocker.patch('src.service.load_file_info', return_value=mock_file)

    # Mock os.path.exists to return True
    mocker.patch('os.path.exists', return_value=True)

    # Test file response
    with patch('src.service.FileResponse') as mock_file_response:
        await get_file_response(mock_session, mock_file.id)

        mock_file_response.assert_called_once_with(
            path=get_file_path(mock_file),
            filename=mock_file.name + mock_file.extension,
            media_type=mock_file.format
        )


@pytest.mark.asyncio
async def test_get_file_response_file_not_found(mocker):
    # Mock dependencies
    mock_session = AsyncMock(spec=AsyncSession)
    mock_file = FileModel(
        id=uuid.uuid4(),
        name='test_file',
        extension='.txt',
        format='text/plain'
    )

    # Mock load_file_info to return the file
    mocker.patch('src.service.load_file_info', return_value=mock_file)

    # Mock os.path.exists to return False
    mocker.patch('os.path.exists', return_value=False)

    # Test file not found raises HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await get_file_response(mock_session, mock_file.id)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_save_file_success(mocker):
    # Mock dependencies
    mock_session = AsyncMock(spec=AsyncSession)

    # Create a mock UploadFile
    mock_upload_file = AsyncMock(spec=UploadFile)
    mock_upload_file.filename = 'test_file.txt'
    mock_upload_file.content_type = 'text/plain'
    mock_upload_file.size = 1024
    mock_upload_file.read = AsyncBytesIO(b'1234').read

    # Mock aiofiles.open
    write_mock = AsyncMock()
    mocker.patch('aiofiles.open', return_value=write_mock)

    # Mock asyncio.create_task
    mock_create_task = mocker.patch('asyncio.create_task')
    mocker.patch('src.service.upload_file_to_storage', new_callable=Mock)

    # Mock the file save process
    with patch('src.service.FileModel') as MockFileModel:
        mock_file_instance = MockFileModel.return_value
        mock_file_instance.id = uuid.uuid4()
        mock_file_instance.name = 'test_file'
        mock_file_instance.extension = '.txt'

        # Test file save
        result = await save_file(mock_session, mock_upload_file)

        # Assertions
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert await mock_upload_file.read() == b''
        mock_create_task.assert_called_once()

        assert result == mock_file_instance


# Utility function tests
def test_get_file_path():
    file = FileModel(id=uuid.uuid4(), extension='.txt')
    expected_path = f"{STATIC_PATH}/{file.id}.txt"
    assert get_file_path(file) == expected_path