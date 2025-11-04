# S3 File Writer MetaAgent

Write files to Amazon Web Services (AWS) S3 cloud storage with configurable paths and file extensions.

## What Does It Do?

This metaagent provides simple file writing capabilities for AWS S3 buckets. You can:
- Write text content to S3
- Write JSON data to S3 (with automatic serialization)
- Write binary data to S3
- Configure default bucket, location (path prefix), and file suffix
- Override configuration per write operation

## How to Use

### Step 1: Initialize (on_create)

Provide your AWS credentials and default configuration:

```python
config = {
    "aws_access_key_id": "YOUR_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_SECRET_KEY",
    "region_name": "us-east-1",  # Optional, defaults to us-east-1
    "bucket": "my-bucket",  # Required
    "location": "outputs/simulations",  # Optional, path prefix
    "file_suffix": ".json"  # Optional, defaults to .json
}

result = on_create(config)
```

**Configuration Parameters:**
- `aws_access_key_id` - Your AWS access key (required)
- `aws_secret_access_key` - Your AWS secret key (required)
- `region_name` - AWS region (optional, defaults to "us-east-1")
- `bucket` - S3 bucket name (required)
- `location` - Path prefix/folder in bucket (optional, defaults to empty)
- `file_suffix` - File extension to append (optional, defaults to ".json")

### Step 2: Write Files (on_receive)

#### Writing JSON Data

```python
data = {
    "content": {
        "timestamp": "2025-01-15T10:30:00",
        "simulation_id": "sim_001",
        "results": {
            "peak_flow": 125.5
        }
    },
    "key": "simulation_results_001"
}

result = on_receive(data)
# Returns: {"status": "success", "s3_path": "s3://my-bucket/outputs/simulations/simulation_results_001.json", ...}
```

The metaagent will:
1. Append the configured suffix (`.json`) to the key
2. Prepend the configured location (`outputs/simulations`)
3. Serialize the content to JSON
4. Write to S3

**Final S3 path:** `s3://my-bucket/outputs/simulations/simulation_results_001.json`

#### Writing String Content

```python
data = {
    "content": "This is a log message\nTimestamp: 2025-01-15T10:30:00",
    "key": "log_001"
}

result = on_receive(data)
```

#### Overriding Configuration

You can override the default bucket, location, or suffix per write:

```python
data = {
    "content": "Alert: High water level",
    "key": "alert_001",
    "location": "alerts",  # Override location
    "file_suffix": ".txt"  # Override suffix
}

result = on_receive(data)
# Writes to: s3://my-bucket/alerts/alert_001.txt
```

**Input Parameters:**
- `content` - Content to write (string, bytes, or JSON-serializable object) (required)
- `key` - Base filename (required)
- `bucket` - Override configured bucket (optional)
- `location` - Override configured location (optional)
- `file_suffix` - Override configured suffix (optional)

**Returns:**
```python
{
    "status": "success",
    "bucket": "my-bucket",
    "key": "outputs/simulations/simulation_results_001.json",
    "size": 245,
    "etag": "d41d8cd98f00b204e9800998ecf8427e",
    "version_id": "...",  # If versioning is enabled
    "s3_path": "s3://my-bucket/outputs/simulations/simulation_results_001.json"
}
```

### Step 3: Clean Up (on_destroy)

```python
result = on_destroy()
```

## Content Types

The metaagent handles different content types automatically:

**1. JSON Objects/Arrays:**
```python
"content": {"key": "value", "number": 123}
# Automatically serialized to formatted JSON
```

**2. String Content:**
```python
"content": "Plain text content"
# Written as UTF-8 encoded text
```

**3. Binary Content:**
```python
"content": b"\x00\x01\x02\x03"
# Written as raw bytes
```

## Path Construction

The final S3 path is constructed as:
```
s3://{bucket}/{location}/{key}{file_suffix}
```

**Examples:**

| Config Location | Config Suffix | Input Key | Final Path |
|----------------|---------------|-----------|------------|
| `outputs/` | `.json` | `data_001` | `s3://bucket/outputs/data_001.json` |
| `` (empty) | `.txt` | `log` | `s3://bucket/log.txt` |
| `results/2025/` | `.csv` | `export` | `s3://bucket/results/2025/export.csv` |

## Common Use Cases

1. **Store Simulation Results** - Save SWMM simulation outputs as JSON to S3
2. **Log Events** - Write log messages or alerts to S3
3. **Export Data** - Save processed data in various formats
4. **Archive Reports** - Store generated reports in organized folder structures
5. **Timestamped Outputs** - Use timestamp-based keys for time-series data

## Example Workflows

### Writing Timestamped Simulation Results

```python
from datetime import datetime

# Initialize
s3_writer.on_create({
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "bucket": "xmtwin",
    "location": "simulations/results",
    "file_suffix": ".json"
})

# Write with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result = s3_writer.on_receive({
    "content": simulation_results,
    "key": f"sim_{timestamp}"
})

# Writes to: s3://xmtwin/simulations/results/sim_20250115_103000.json
```

### Writing to Different Locations

```python
# Configure with default location
s3_writer.on_create({
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "bucket": "xmtwin",
    "location": "outputs",
    "file_suffix": ".json"
})

# Write to default location
s3_writer.on_receive({
    "content": data,
    "key": "normal_output"
})
# -> s3://xmtwin/outputs/normal_output.json

# Override for alerts
s3_writer.on_receive({
    "content": alert_data,
    "key": "alert_001",
    "location": "alerts",
    "file_suffix": ".txt"
})
# -> s3://xmtwin/alerts/alert_001.txt
```

## Tips

- Store AWS credentials securely (use environment variables in production)
- Use meaningful key names for easier file management
- Organize data with location prefixes (folders)
- Use timestamp-based keys for time-series data
- The metaagent automatically handles JSON serialization for dict/list objects
- File suffixes are automatically appended if not already present on the key

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
- Insufficient write permissions
- Missing required parameters (content or key)
- Invalid content type

## Security Notes

- Never commit AWS credentials to version control
- Use IAM roles with minimal required permissions (s3:PutObject)
- Consider using temporary credentials (STS) for production
- Regularly rotate access keys
- Enable S3 bucket versioning for important data
- Consider enabling S3 encryption at rest

## Dependencies

Requires the `boto3` Python package:
```bash
pip install boto3
```

## Integration with Other MetaAgents

This metaagent works well with other metaagents in the pipeline:

1. **After PySWMM Simulation** - Write simulation results to S3
2. **After Weather Generation** - Store weather data in S3
3. **For Logging** - Write processing logs or alerts to S3
4. **With S3 File Access** - Write files and then read them back for verification

## Complete Example

```python
from metaagents.aws.s3.file_writer import metaagent as s3_writer
from datetime import datetime

# Initialize
s3_writer.on_create({
    "aws_access_key_id": "YOUR_KEY",
    "aws_secret_access_key": "YOUR_SECRET",
    "region_name": "us-east-1",
    "bucket": "xmtwin",
    "location": "water_utilities/flood_management",
    "file_suffix": ".json"
})

# Write simulation results
results = {
    "timestamp": datetime.now().isoformat(),
    "simulation_id": "sim_001",
    "peak_flow": 125.5,
    "total_volume": 1500.2
}

response = s3_writer.on_receive({
    "content": results,
    "key": f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
})

print(f"Wrote to: {response['s3_path']}")
print(f"Size: {response['size']} bytes")
print(f"ETag: {response['etag']}")

# Clean up
s3_writer.on_destroy()
```
