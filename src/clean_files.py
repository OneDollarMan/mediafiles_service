import os
from datetime import datetime, timedelta
from src.config import STATIC_PATH, FILE_EXPIRATION_DAYS


def delete_old_files(directory: str, expiration_days: int):
    """Cleans expired files"""
    now = datetime.now()
    expiration_time = now - timedelta(days=expiration_days)
    deleted_files = 0

    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))  # Last change time
                if file_mtime < expiration_time:
                    os.remove(file_path)
                    print(f"File removed: {file_path}")
                    deleted_files += 1
            except Exception as e:
                print(f"File remove error: {file_path}: {e}")

    print(f"Cleaning finished. Files removed: {deleted_files}")


if __name__ == "__main__":
    delete_old_files(STATIC_PATH, FILE_EXPIRATION_DAYS)