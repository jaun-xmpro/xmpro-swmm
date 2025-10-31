# S3 File Access MetaAgent

Read and list files stored in Amazon Web Services (AWS) S3 cloud storage.

## What Does It Do?

This metaagent provides simple access to files stored in AWS S3 buckets. You can:
- Read file contents from S3
- List files in an S3 folder (prefix)
- Optionally decode text files or get raw binary data

## How to Use

### Step 1: Initialize (on_create)

Provide your AWS credentials and default bucket:

```python
config = {
    "aws_access_key_id": "YOUR_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_SECRET_KEY",
    "region_name": "us-east-1",  # Optional, defaults to us-east-1
    "bucket": "my-bucket"  # Optional, can specify per request
}

result = on_create(config)
```

**Configuration Parameters:**
- `aws_access_key_id` - Your AWS access key (required)
- `aws_secret_access_key` - Your AWS secret key (required)
- `region_name` - AWS region (optional, defaults to "us-east-1")
- `bucket` - Default S3 bucket name (optional, can override per request)

### Step 2: Read or List Files (on_receive)

#### Reading a File

```python
data = {
    "operation": "read_file",
    "s3_path": "s3://my-bucket/path/to/file.txt",
    "decode": True  # Optional, defaults to True
}

result = on_receive(data)
# Returns: {"status": "success", "content": "file contents...", ...}
```

**Alternative format using bucket and key separately:**
```python
data = {
    "operation": "read_file",
    "bucket": "my-bucket",
    "key": "path/to/file.txt",
    "decode": True
}
```

**Parameters:**
- `operation` - "read_file" (default if not specified)
- `s3_path` - Full S3 path like "s3://bucket/key" OR
- `bucket` + `key` - Bucket and key specified separately
- `decode` - If True (default), returns text content. If False, returns hex-encoded binary data

#### Listing Files

```python
data = {
    "operation": "list_files",
    "s3_path": "s3://my-bucket/reports/",
    # OR: "bucket": "my-bucket", "prefix": "reports/"
}

result = on_receive(data)
```

**Returns:**
```python
{
    "status": "success",
    "operation": "list_files",
    "bucket": "my-bucket",
    "prefix": "reports/",
    "files": [
        {
            "key": "reports/simulation_001.rpt",
            "size": 15420,
            "last_modified": "2025-01-15T10:30:00"
        },
        {
            "key": "reports/simulation_002.rpt",
            "size": 16832,
            "last_modified": "2025-01-15T11:45:00"
        }
    ],
    "count": 2
}
```

### Step 3: Clean Up (on_destroy)

```python
result = on_destroy()
```

## S3 Path Formats

You can specify S3 locations in two ways:

**1. Full S3 path:**
```python
"s3_path": "s3://bucket-name/folder/file.txt"
# or without s3:// prefix:
"s3_path": "bucket-name/folder/file.txt"
```

**2. Separate bucket and key:**
```python
"bucket": "bucket-name",
"key": "folder/file.txt"
```

## Common Use Cases

1. **Read Simulation Results** - Download and read SWMM report files from S3
2. **List Available Runs** - See what simulation outputs are available
3. **Access Configuration Files** - Read SWMM .inp files stored in S3
4. **Download Binary Data** - Get .out files or other binary formats

## Reading Text vs Binary Files

**Text files** (decode=True):
- Returns actual text content
- Good for: .rpt files, .inp files, .txt, .json, .csv, etc.
- Content is decoded as UTF-8

**Binary files** (decode=False):
- Returns hex-encoded binary data
- Good for: .out files, compressed files, images, etc.
- You'll need to decode the hex string and process the bytes

## Tips

- Store your AWS credentials securely (use environment variables in production)
- The default bucket set in `on_create` can be overridden in each `on_receive` call
- When listing files, the prefix parameter acts like a folder filter
- File sizes are returned in bytes

## Error Handling

If something goes wrong, you'll get an error response:

```python
{
    "status": "error",
    "message": "Description of what went wrong"
}
```

Common errors:
- Invalid credentials
- Bucket doesn't exist
- File not found
- Insufficient permissions

## Example Workflow

```python
# 1. Initialize with credentials
s3_access.on_create({
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "bucket": "xmtwin"
})

# 2. List simulation results
files = s3_access.on_receive({
    "operation": "list_files",
    "prefix": "water_utilities/flood_management/"
})

# 3. Read a specific report
report = s3_access.on_receive({
    "operation": "read_file",
    "key": "water_utilities/flood_management/2025-01-15T143000Z/network_mod.rpt"
})

# 4. Process the report content
print(report["content"])
```

## Security Notes

- Never commit AWS credentials to version control
- Use IAM roles with minimal required permissions
- Consider using temporary credentials (STS) for production
- Regularly rotate access keys

## Dependencies

Requires the `boto3` Python package:
```bash
pip install boto3
```
