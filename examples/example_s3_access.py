"""
Example: Accessing Files from AWS S3

This example demonstrates how to:
1. Initialize S3 access with credentials
2. List files in a bucket/prefix
3. Read a file from S3

Note: You need valid AWS credentials to run this example.
"""

import sys
from pathlib import Path

# Add parent directory to path to import metaagents
sys.path.insert(0, str(Path(__file__).parent.parent))

from metaagents.aws.s3.file_access import metaagent as s3_access


def main():
    print("=" * 60)
    print("S3 File Access Example")
    print("=" * 60)

    # IMPORTANT: Update these with your AWS credentials
    AWS_ACCESS_KEY_ID = "your_access_key"
    AWS_SECRET_ACCESS_KEY = "your_secret_key"
    AWS_REGION = "us-east-1"
    BUCKET = "xmtwin"
    PREFIX = "water_utilities/flood_management/"

    # Step 1: Initialize S3 access
    print("\n1. Initializing S3 access...")
    result = s3_access.on_create({
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": AWS_REGION,
        "bucket": BUCKET
    })

    if result['status'] == 'error':
        print(f"   Error: {result['message']}")
        return

    print(f"   Status: {result['status']}")
    print(f"   Region: {result['region']}")
    print(f"   Default bucket: {result['default_bucket']}")

    # Step 2: List files in a prefix
    print(f"\n2. Listing files in s3://{BUCKET}/{PREFIX}...")
    list_result = s3_access.on_receive({
        "operation": "list_files",
        "prefix": PREFIX
    })

    if list_result['status'] == 'error':
        print(f"   Error: {list_result['message']}")
        return

    print(f"   Found {list_result['count']} files:")

    for file_info in list_result['files'][:10]:  # Show first 10 files
        size_kb = file_info['size'] / 1024
        print(f"      {file_info['key']}")
        print(f"         Size: {size_kb:.2f} KB")
        print(f"         Modified: {file_info['last_modified']}")

    # Step 3: Read a specific file
    if list_result['count'] > 0:
        # Read the first .rpt file found
        rpt_files = [f for f in list_result['files'] if f['key'].endswith('.rpt')]

        if rpt_files:
            print(f"\n3. Reading report file...")
            file_to_read = rpt_files[0]['key']
            print(f"   File: {file_to_read}")

            read_result = s3_access.on_receive({
                "operation": "read_file",
                "key": file_to_read,
                "decode": True
            })

            if read_result['status'] == 'error':
                print(f"   Error: {read_result['message']}")
            else:
                print(f"   Successfully read file ({read_result['size']} bytes)")
                print("\n   First 500 characters:")
                print("   " + "-" * 56)
                print(read_result['content'][:500])
                print("   " + "-" * 56)

    # Alternative: Read using full S3 path
    print("\n4. Alternative: Reading using full S3 path...")
    print("   Example (not executed):")
    print(f"   s3_access.on_receive({{")
    print(f"       'operation': 'read_file',")
    print(f"       's3_path': 's3://{BUCKET}/{PREFIX}2025-01-15T143000Z/network_mod.rpt'")
    print(f"   }})")

    # Cleanup
    print("\n5. Cleaning up...")
    s3_access.on_destroy()

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
