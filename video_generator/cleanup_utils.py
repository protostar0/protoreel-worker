"""
Cleanup utilities for ProtoVideo.
Handles deletion of temporary files and memory cleanup.
"""
from typing import List
import os
import logging

def cleanup_files(filepaths: List[str]) -> None:
    """
    Delete a list of files from disk if they exist.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Cleaning up {len(filepaths)} temp files...")
    for path in filepaths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete temp file {path}: {e}")

def upload_to_r2(local_file_path, bucket_name, object_key):
    import boto3
    import os
    import logging
    logger = logging.getLogger(__name__)
    session = boto3.session.Session()
    client = session.client(
        service_name='s3',
        endpoint_url=os.environ.get('R2_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('R2_SECRET_ACCESS_KEY'),
    )
    client.upload_file(local_file_path, bucket_name, object_key)
    logger.info(f"✅ Uploaded to R2: {bucket_name}/{object_key}")
    r2_public_base = os.environ.get('R2_PUBLIC_BASE_URL')
    if r2_public_base:
        return f"{r2_public_base.rstrip('/')}/{object_key}"
    return None 