"""
S3 File Access Metaagent for XMPro DataStreams
Jaun van Heerden, 2025

A metaagent for accessing and reading files from AWS S3 buckets.
Provides general file access capabilities for S3 storage.

Changelog:
    v0.1 - 2025/10/29 - Initial version with S3 file read capabilities
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
from io import BytesIO

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# --- Data Classes ---
@dataclass
class S3Config:
    """Configuration for S3 connection."""
    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str = "us-east-1"
    bucket: str = ""


@dataclass
class S3State:
    """Global state management for the metaagent."""
    config: S3Config | None = None
    s3_client: Any = None

    def reset(self) -> None:
        """Reset state to initial condition."""
        self.config = None
        self.s3_client = None


# Global state instance
_state = S3State()


# --- Helper Functions ---
def _parse_s3_path(s3_path: str) -> tuple[str, str]:
    """
    Parse S3 path into bucket and key.

    Args:
        s3_path: S3 path in format 's3://bucket/key' or 'bucket/key'

    Returns:
        Tuple of (bucket, key)
    """
    if s3_path.startswith('s3://'):
        s3_path = s3_path[5:]

    parts = s3_path.split('/', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], ''
    else:
        raise ValueError(f"Invalid S3 path: {s3_path}")


def read_file_from_s3(s3_client: Any, bucket: str, key: str, decode: bool = True) -> str | bytes:
    """
    Read a file from S3.

    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        key: S3 object key
        decode: If True, decode as UTF-8 string; if False, return bytes

    Returns:
        File contents as string or bytes

    Raises:
        Exception: If file cannot be read from S3
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()

        if decode:
            return content.decode('utf-8')
        else:
            return content

    except Exception as e:
        logger.error(f"Failed to read s3://{bucket}/{key}: {e}")
        raise


def list_files_in_s3_prefix(s3_client: Any, bucket: str, prefix: str) -> list[dict[str, Any]]:
    """
    List all files in an S3 prefix.

    Args:
        s3_client: Boto3 S3 client instance
        bucket: S3 bucket name
        prefix: S3 prefix (folder path)

    Returns:
        List of file information dicts with 'key', 'size', and 'last_modified'
    """
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        if 'Contents' not in response:
            return []

        files = []
        for obj in response['Contents']:
            files.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat()
            })

        return files

    except Exception as e:
        logger.error(f"Failed to list files in s3://{bucket}/{prefix}: {e}")
        raise


# --- Metaagent Interface Functions ---
def on_create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Initialize the metaagent with S3 configuration.

    Expected data format:
    {
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY",
        "region_name": "us-east-1",  # optional, defaults to us-east-1
        "bucket": "your-bucket-name"  # optional, can be provided per request
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

    if not aws_access_key_id or not aws_secret_access_key:
        return {
            'status': 'error',
            'message': 'aws_access_key_id and aws_secret_access_key are required'
        }

    try:
        import boto3

        # Create S3Config
        s3_config = S3Config(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            bucket=bucket
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

        logger.info(f"S3 metaagent initialized: region={region_name}")

        return {
            'status': 'initialized',
            'region': region_name,
            'default_bucket': bucket if bucket else None
        }

    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def on_receive(data: dict[str, Any]) -> dict[str, Any]:
    """
    Execute S3 file operations.

    Expected data format:
    {
        "operation": "read_file" | "list_files",

        # For read_file operation:
        "s3_path": "s3://bucket/path/to/file" or "bucket/path/to/file",
        # OR
        "bucket": "bucket-name",
        "key": "path/to/file",

        "decode": true,  # optional, default true - decode as UTF-8 string

        # For list_files operation:
        "s3_path": "s3://bucket/prefix/" or "bucket/prefix/",
        # OR
        "bucket": "bucket-name",
        "prefix": "path/to/prefix/"
    }

    Args:
        data: Data dictionary with operation details

    Returns:
        Results dictionary with file contents or file list

    Raises:
        RuntimeError: If metaagent not initialized or operation fails
    """
    global _state

    if _state.s3_client is None:
        return {
            'status': 'error',
            'message': 'S3 metaagent not initialized. Call on_create() first.'
        }

    operation = data.get('operation', 'read_file')

    try:
        if operation == 'read_file':
            # Get bucket and key
            s3_path = data.get('s3_path')
            if s3_path:
                bucket, key = _parse_s3_path(s3_path)
            else:
                bucket = data.get('bucket', _state.config.bucket)
                key = data.get('key', '')

            if not bucket or not key:
                return {
                    'status': 'error',
                    'message': 'Bucket and key are required for read_file operation'
                }

            decode = data.get('decode', True)

            content = read_file_from_s3(_state.s3_client, bucket, key, decode=decode)

            return {
                'status': 'success',
                'operation': 'read_file',
                'bucket': bucket,
                'key': key,
                'content': content if decode else content.hex(),
                'size': len(content),
                'decoded': decode
            }

        elif operation == 'list_files':
            # Get bucket and prefix
            s3_path = data.get('s3_path')
            if s3_path:
                bucket, prefix = _parse_s3_path(s3_path)
            else:
                bucket = data.get('bucket', _state.config.bucket)
                prefix = data.get('prefix', '')

            if not bucket:
                return {
                    'status': 'error',
                    'message': 'Bucket is required for list_files operation'
                }

            files = list_files_in_s3_prefix(_state.s3_client, bucket, prefix)

            return {
                'status': 'success',
                'operation': 'list_files',
                'bucket': bucket,
                'prefix': prefix,
                'files': files,
                'count': len(files)
            }

        else:
            return {
                'status': 'error',
                'message': f'Unknown operation: {operation}. Supported: read_file, list_files'
            }

    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
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
    logger.info("S3 metaagent destroyed")

    return {'status': 'destroyed'}
