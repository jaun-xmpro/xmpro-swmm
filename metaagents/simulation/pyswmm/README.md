# PySWMM Simulation MetaAgent

Run SWMM (Storm Water Management Model) hydraulic simulations with dynamic modifications and automatic cloud storage of results.

## What Does It Do?

This metaagent:
- Runs SWMM simulations using your model file (.inp)
- Applies dynamic modifications (weather data, simulation settings, etc.)
- Extracts detailed results (flow rates, depths, flooding, etc.)
- Uploads all results and files to AWS S3 for easy access
- Returns a simple S3 path to the report file

It supports loading SWMM models from multiple sources: local files, S3, GitHub, or any HTTP URL.

## How to Use

### Step 1: Initialize (on_create)

Configure your SWMM model source and AWS settings:

```python
config = {
    # SWMM Model Configuration
    "network_file": "path/to/model.inp",
    "source_type": "local",  # Options: "local", "s3", "github", "http"

    # AWS S3 Configuration (optional but recommended)
    "aws_access_key_id": "YOUR_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_SECRET_KEY",
    "region_name": "us-east-1",
    "bucket": "xmtwin",
    "prefix_base": "water_utilities/flood_management"
}

result = on_create(config)
```

**Model Source Types:**

1. **Local File:**
```python
"network_file": "C:/models/mymodel.inp",
"source_type": "local"
```

2. **S3:**
```python
"network_file": "s3://my-bucket/models/mymodel.inp",
"source_type": "s3"
```

3. **GitHub:**
```python
"network_file": "https://github.com/user/repo/blob/main/model.inp",
"source_type": "github"
```

4. **HTTP:**
```python
"network_file": "https://example.com/models/mymodel.inp",
"source_type": "http"
```

**AWS S3 Settings** (optional):
- `aws_access_key_id` - Your AWS access key
- `aws_secret_access_key` - Your AWS secret key
- `region_name` - AWS region (default: "us-east-1")
- `bucket` - S3 bucket for results (default: "xmtwin")
- `prefix_base` - Base path in bucket (default: "water_utilities/flood_management")

### Step 2: Run Simulation (on_receive)

Run the simulation with optional modifications:

```python
data = {
    "modifications": {
        "options": {
            "start_date": "01/15/2025",
            "start_time": "00:00:00",
            "end_date": "01/16/2025",
            "end_time": "00:00:00",
            "report_step": "00:15:00"
        },
        "timeseries": {
            "rain1": [
                "01/15/2025  00:00:00     0.00",
                "01/15/2025  01:00:00     5.20",
                "01/15/2025  02:00:00     8.50",
                # ... more timesteps
            ],
            "rain2": [...]
        }
    }
}

result = on_receive(data)
```

**Modifications:**
- `options` - SWMM OPTIONS section parameters (dates, times, report steps, etc.)
- `timeseries` - Weather data or other timeseries inputs

**If you have weather data from the converter:**
```python
# Get modifications from Weather to PySWMM converter
weather_data = weather_to_pyswmm.on_receive({...})

# Pass directly to simulation
result = pyswmm_simulation.on_receive({
    "modifications": weather_data["modifications"]
})
```

### Step 3: Access Results

The simulation returns a simple result with the S3 path to the report:

```python
{
    "status": "completed",
    "run_id": "2025-01-15T143000Z",
    "rpt_s3_path": "s3://xmtwin/water_utilities/flood_management/2025-01-15T143000Z/network_mod.rpt"
}
```

You can then use the S3 File Access metaagent to read the report:

```python
report = s3_access.on_receive({
    "operation": "read_file",
    "s3_path": result["rpt_s3_path"]
})
```

## What Gets Uploaded to S3

For each simulation run, the following files are stored in S3:

1. **network_mod.rpt** - SWMM text report with summary and analysis
2. **network_mod.inp** - Modified input file used for the simulation
3. **network_mod.out** - Binary output file with detailed timeseries
4. **JSON Results** (in gzipped format):
   - `system.json.gz` - System-wide metrics (rainfall, total flows, etc.)
   - `subcatchments.json.gz` - Data for each subcatchment
   - `nodes.json.gz` - Data for each node
   - `links.json.gz` - Data for each link/pipe
   - `manifest.json` - Index of available data files

All files are stored under: `s3://{bucket}/{prefix_base}/{run_id}/`

## Exported Data

The metaagent extracts comprehensive timeseries data:

**System Attributes:**
- Rainfall
- Runoff flow
- Outfall flows
- Snow depth

**Subcatchment Attributes:**
- Rainfall
- Runoff rate
- Snow depth
- Evaporation loss
- Infiltration loss
- Soil moisture

**Node Attributes:**
- Invert depth
- Hydraulic head
- Total inflow
- Lateral inflow
- Flooding losses

**Link Attributes:**
- Flow rate
- Flow depth
- Flow velocity
- Flow volume

## Common OPTIONS Modifications

```python
"options": {
    # Simulation period
    "start_date": "01/15/2025",
    "start_time": "00:00:00",
    "end_date": "01/16/2025",
    "end_time": "00:00:00",

    # Reporting
    "report_start_date": "01/15/2025",
    "report_start_time": "00:00:00",
    "report_step": "00:15:00",  # Report every 15 minutes

    # Routing
    "routing_step": "00:00:30",  # 30 seconds
    "min_route_step": "00:00:05",  # 5 seconds

    # Other settings
    "allow_ponding": "YES",
    "min_slope": "0.0001"
}
```

## Tips

- Use smaller `report_step` values for more detailed output (but larger file sizes)
- The `run_id` is based on the current timestamp when simulation starts
- All uploaded files use consistent naming (`network_mod.*`) regardless of original filename
- JSON files are gzip-compressed to save space and reduce upload time
- If S3 is not configured, simulation still runs but results won't be uploaded

## Error Handling

If the simulation fails, you'll get an error status:

```python
{
    "status": "error",
    "message": "Description of what went wrong"
}
```

Common issues:
- Invalid SWMM model file
- Network file not found
- Missing AWS credentials (if trying to upload)
- SWMM errors (routing issues, negative depths, etc.)

## Example Full Workflow

```python
# 1. Initialize simulation
pyswmm.on_create({
    "network_file": "s3://my-bucket/models/city_model.inp",
    "source_type": "s3",
    "aws_access_key_id": "...",
    "aws_secret_access_key": "...",
    "bucket": "results-bucket"
})

# 2. Generate weather
weather = weather_simulation.on_receive({...})

# 3. Interpolate weather
interpolated = weather_interpolation.on_receive({...})

# 4. Convert to SWMM format
swmm_weather = weather_to_pyswmm.on_receive({...})

# 5. Run simulation with weather
result = pyswmm.on_receive({
    "modifications": swmm_weather["modifications"]
})

# 6. Read the report
report = s3_access.on_receive({
    "operation": "read_file",
    "s3_path": result["rpt_s3_path"]
})

print(report["content"])
```

## Dependencies

```bash
pip install pyswmm boto3
```

## Performance Notes

- Simulation time depends on model size and complexity
- Large models with small time steps can take several minutes
- Results are uploaded to S3 after simulation completes
- Compressed JSON files typically reduce size by 80-90%

## Cleanup

When done, clean up resources:

```python
pyswmm.on_destroy()
```

This removes temporary files if the model was downloaded from a remote source.
