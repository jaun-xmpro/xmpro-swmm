# S3 File Writer MetaAgent

Write files to Amazon Web Services (AWS) S3 cloud storage.

## What Does It Do?

This metaagent provides simple file writing capabilities for AWS S3 buckets. You can:
- Write text content to S3
- Write JSON data to S3 (with automatic serialization)
- Write binary data to S3
- Specify full S3 paths including folders and file extensions

## How to Use

### Step 1: Initialize (on_create)

Provide your AWS credentials and target bucket:

```python
config = {
    "aws_access_key_id": "YOUR_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_SECRET_KEY",
    "region_name": "us-east-1",  # Optional, defaults to us-east-1
    "bucket": "my-bucket"
}

result = on_create(config)
```

**Configuration Parameters:**
- `aws_access_key_id` - Your AWS access key (required)
- `aws_secret_access_key` - Your AWS secret key (required)
- `region_name` - AWS region (optional, defaults to "us-east-1")
- `bucket` - S3 bucket name (required)

### Step 2: Write Files (on_receive)

#### Writing JSON Data

```python
data = {
    "content": {
        "timestamp": "2025-01-15T10:30:00",
        "simulation_id": "sim_001",
        "results": {"peak_flow": 125.5}
    },
    "key": "outputs/simulations/simulation_results_001.json"
}

result = on_receive(data)
# Writes to: s3://my-bucket/outputs/simulations/simulation_results_001.json
```

The metaagent will:
1. Serialize the dict/list to JSON automatically
2. Write to S3 at the specified key path

#### Writing String Content

```python
data = {
    "content": "This is a log message\nTimestamp: 2025-01-15T10:30:00",
    "key": "logs/process_log.txt"
}

result = on_receive(data)
# Writes to: s3://my-bucket/logs/process_log.txt
```

#### Writing to Different Paths

The key can include any path structure you need:

```python
# Write to nested folders
s3_writer.on_receive({
    "content": alert_data,
    "key": "water_utilities/flood_management/alerts/alert_001.json"
})

# Write with timestamp in path
s3_writer.on_receive({
    "content": weather_data,
    "key": f"weather/data/{datetime.now().strftime('%Y/%m/%d')}/weather.json"
})

# Write CSV data
s3_writer.on_receive({
    "content": "name,value\ntest,123",
    "key": "exports/data.csv"
})
```

**Input Parameters:**
- `content` - Content to write (string, bytes, or JSON-serializable object) (required)
- `key` - Full S3 path including folders and file extension (required)

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

## Path Examples

| Key | Final S3 Path |
|-----|---------------|
| `data.json` | `s3://bucket/data.json` |
| `outputs/result.json` | `s3://bucket/outputs/result.json` |
| `logs/2025/01/15/app.log` | `s3://bucket/logs/2025/01/15/app.log` |
| `exports/data.csv` | `s3://bucket/exports/data.csv` |

## Common Use Cases

1. **Store Simulation Results** - Save SWMM simulation outputs as JSON to S3
2. **Log Events** - Write log messages to organized folder structures
3. **Export Data** - Save processed data in various formats (JSON, CSV, TXT)
4. **Archive Reports** - Store generated reports with timestamp-based paths
5. **Time-Series Data** - Use date-based paths for time-series organization

## Example Workflows

### Writing Timestamped Simulation Results

```python
from datetime import datetime

# Initialize
s3_writer.on_create({
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "bucket": "xmtwin"
})

# Write with timestamp in path
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result = s3_writer.on_receive({
    "content": simulation_results,
    "key": f"simulations/results/sim_{timestamp}.json"
})

# Writes to: s3://xmtwin/simulations/results/sim_20250115_103000.json
```

### Writing to Organized Folder Structure

```python
# Organize by date and type
date_path = datetime.now().strftime("%Y/%m/%d")

# Write simulation output
s3_writer.on_receive({
    "content": sim_data,
    "key": f"water_utilities/simulations/{date_path}/output.json"
})

# Write alert
s3_writer.on_receive({
    "content": alert_data,
    "key": f"water_utilities/alerts/{date_path}/alert.json"
})

# Write log
s3_writer.on_receive({
    "content": log_text,
    "key": f"water_utilities/logs/{date_path}/process.log"
})
```

### Writing Different File Types

```python
# JSON data
s3_writer.on_receive({
    "content": {"data": "value"},
    "key": "outputs/data.json"
})

# CSV data
s3_writer.on_receive({
    "content": "col1,col2\nval1,val2",
    "key": "exports/data.csv"
})

# Text log
s3_writer.on_receive({
    "content": "Log entry: Process completed",
    "key": "logs/app.log"
})

# Markdown report
s3_writer.on_receive({
    "content": "# Report\n\nResults: Success",
    "key": "reports/summary.md"
})
```

## Tips

- Store AWS credentials securely (use environment variables in production)
- Include file extensions in the key (e.g., `.json`, `.csv`, `.txt`)
- Organize files with folder paths in the key for better structure
- Use timestamp-based keys for time-series data
- The metaagent automatically handles JSON serialization for dict/list objects
- Include meaningful paths to make files easy to find and manage

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
3. **For Logging** - Write processing logs to S3
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
    "bucket": "xmtwin"
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
    "key": f"simulations/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
})

print(f"Wrote to: {response['s3_path']}")
print(f"Size: {response['size']} bytes")
print(f"ETag: {response['etag']}")

# Clean up
s3_writer.on_destroy()
```
