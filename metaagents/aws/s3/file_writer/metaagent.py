"""
S3 File Writer Metaagent for XMPro DataStreams
Jaun van Heerden, 2025

A metaagent for writing files to AWS S3 buckets.
Provides file writing capabilities with configurable path, suffix, and content.

Changelog:
    v0.1 - 2025/11/05 - Initial version with S3 file write capabilities
"""

from __future__ import annotations

# --- dataclass runtime guard (fixes NoneType __dict__ crash) ---
import sys, types
if not isinstance(__name__, str) or __name__ not in sys.modules:
    module_name = "xmtwin_runtime"  # any stable name is fine
    globals()["__name__"] = module_name
    mod = types.ModuleType(module_name)
    mod.__dict__.update(globals())
    sys.modules[module_name] = mod
# --- end guard ---

import json
import logging
from dataclasses import dataclass
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# --- Data Classes ---
@dataclass
class S3WriterConfig:
    """Configuration for S3 file writer."""
    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str = "us-east-1"
    bucket: str = ""
    location: str = ""  # Path prefix/folder in bucket
    file_suffix: str = ".json"  # File extension to append


@dataclass
class S3WriterState:
    """Global state management for the metaagent."""
    config: S3WriterConfig | None = None
    s3_client: Any = None

    def reset(self) -> None:
        """Reset state to initial condition."""
        self.config = None
        self.s3_client = None


# Global state instance
_state = S3WriterState()


# --- Helper Functions ---
def write_file_to_s3(s3_client: Any, bucket: str, key: str, content: str | bytes) -> dict[str, Any]:
    """
    Write a file to S3.

    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: S3 object key (full path)
        content: Content to write (string or bytes)

    Returns:
        Dictionary with write results including ETag and file size

    Raises:
        Exception: If file cannot be written to S3
    """
    try:
        # Convert string to bytes if needed
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        # Write to S3
        response = s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content_bytes
        )

        logger.info(f"Successfully wrote to s3://{bucket}/{key}")

        return {
            'etag': response.get('ETag', '').strip('"'),
            'size': len(content_bytes),
            'version_id': response.get('VersionId')
        }

    except Exception as e:
        logger.error(f"Failed to write to s3://{bucket}/{key}: {e}")
        raise


def build_s3_key(location: str, key: str, suffix: str) -> str:
    """
    Build the full S3 key from location, key, and suffix.

    Args:
        location: Path prefix/folder
        key: Base file key/name
        suffix: File extension

    Returns:
        Full S3 key path
    """
    # Ensure key has the suffix
    if suffix and not key.endswith(suffix):
        key = f"{key}{suffix}"

    # Combine location and key
    if location:
        # Ensure location doesn't end with / and doesn't start with /
        location = location.strip('/')
        full_key = f"{location}/{key}"
    else:
        full_key = key

    return full_key


# --- Metaagent Interface Functions ---
def on_create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Initialize the metaagent with S3 writer configuration.

    Expected data format:
    {
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY",
        "region_name": "us-east-1",  # optional, defaults to us-east-1
        "bucket": "your-bucket-name",
        "location": "path/prefix/folder",  # optional, path prefix in bucket
        "file_suffix": ".json"  # optional, file extension (default: .json)
    }

    Args:
        data: Configuration dictionary

    Returns:
        Status dictionary with initialization results
    """
    global _state

    # Extract S3 configuration parameters
    aws_access_key_id = data.get('aws_access_key_id')
    aws_secret_access_key = data.get('aws_secret_access_key')
    region_name = data.get('region_name', 'us-east-1')
    bucket = data.get('bucket', '')
    location = data.get('location', '')
    file_suffix = data.get('file_suffix', '.json')

    if not aws_access_key_id or not aws_secret_access_key:
        return {
            'status': 'error',
            'message': 'aws_access_key_id and aws_secret_access_key are required'
        }

    if not bucket:
        return {
            'status': 'error',
            'message': 'bucket is required'
        }

    try:
        import boto3

        # Create S3WriterConfig
        s3_config = S3WriterConfig(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            bucket=bucket,
            location=location,
            file_suffix=file_suffix
        )

        # Create S3 client
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=s3_config.aws_access_key_id,
            aws_secret_access_key=s3_config.aws_secret_access_key,
            region_name=s3_config.region_name
        )

        _state.config = s3_config
        _state.s3_client = s3_client

        logger.info(f"S3 file writer metaagent initialized: bucket={bucket}, location={location}, suffix={file_suffix}")

        return {
            'status': 'initialized',
            'region': region_name,
            'bucket': bucket,
            'location': location,
            'file_suffix': file_suffix
        }

    except Exception as e:
        logger.error(f"Failed to initialize S3 writer client: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def on_receive(data: dict[str, Any]) -> dict[str, Any]:
    """
    Write content to S3 with the specified key.

    Expected data format:
    {
        "content": "content to write",  # string or will be JSON serialized
        "key": "filename",  # base filename (suffix will be appended from config)

        # Optional overrides:
        "bucket": "override-bucket",  # override configured bucket
        "location": "override/path",  # override configured location
        "file_suffix": ".txt"  # override configured suffix
    }

    Args:
        data: Data dictionary with content and key

    Returns:
        Results dictionary with write confirmation

    Raises:
        RuntimeError: If metaagent not initialized or write fails
    """
    global _state

    if _state.s3_client is None or _state.config is None:
        return {
            'status': 'error',
            'message': 'S3 file writer metaagent not initialized. Call on_create() first.'
        }

    # Extract required parameters
    content = data.get('content')
    key = data.get('key')

    if content is None:
        return {
            'status': 'error',
            'message': 'content is required'
        }

    if not key:
        return {
            'status': 'error',
            'message': 'key is required'
        }

    # Get bucket, location, and suffix (allow overrides)
    bucket = data.get('bucket', _state.config.bucket)
    location = data.get('location', _state.config.location)
    file_suffix = data.get('file_suffix', _state.config.file_suffix)

    try:
        # Build full S3 key
        full_key = build_s3_key(location, key, file_suffix)

        # Convert content to string if it's not already
        if not isinstance(content, (str, bytes)):
            # Assume it's a dict/list that needs JSON serialization
            content = json.dumps(content, indent=2)

        # Write to S3
        write_result = write_file_to_s3(_state.s3_client, bucket, full_key, content)

        return {
            'status': 'success',
            'bucket': bucket,
            'key': full_key,
            'size': write_result['size'],
            'etag': write_result['etag'],
            'version_id': write_result.get('version_id'),
            's3_path': f"s3://{bucket}/{full_key}"
        }

    except Exception as e:
        logger.error(f"Write operation failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


def on_destroy(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Clean up metaagent resources.

    Args:
        data: Optional data dictionary (unused)

    Returns:
        Status dictionary
    """
    global _state

    if _state.config is None:
        return {'status': 'already_destroyed'}

    # Reset state
    _state.reset()
    logger.info("S3 file writer metaagent destroyed")

    return {'status': 'destroyed'}
