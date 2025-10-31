# Example Scripts

This directory contains example scripts demonstrating how to use the XMPro SWMM MetaAgents.

## Available Examples

### 1. Weather Pipeline (`example_weather_pipeline.py`)

A complete workflow for generating and interpolating weather data without running a SWMM simulation.

**What it demonstrates:**
- Initializing the weather simulation metaagent
- Generating weather for multiple observation areas
- Interpolating weather to specific query points
- Viewing the results

**How to run:**
```bash
python examples/example_weather_pipeline.py
```

**Requirements:**
- No SWMM model file needed
- No AWS credentials needed

### 2. SWMM Simulation (`example_swmm_simulation.py`)

A complete end-to-end workflow including weather generation and SWMM simulation.

**What it demonstrates:**
- Full pipeline from weather generation to simulation
- Converting weather data to SWMM format
- Running a SWMM simulation with custom weather
- Uploading results to S3 (optional)

**How to run:**
```bash
python examples/example_swmm_simulation.py
```

**Requirements:**
- SWMM model file (.inp) - Update `NETWORK_FILE` path in the script
- AWS credentials (optional, for S3 upload)

**Before running:**
1. Open the script
2. Update `NETWORK_FILE` to point to your SWMM model
3. (Optional) Add AWS credentials if you want to upload results to S3
4. Update the `query` point names to match your SWMM timeseries names

### 3. S3 File Access (`example_s3_access.py`)

Demonstrates reading and listing files from AWS S3.

**What it demonstrates:**
- Initializing S3 access
- Listing files in an S3 bucket/prefix
- Reading file contents from S3
- Different ways to specify S3 paths

**How to run:**
```bash
python examples/example_s3_access.py
```

**Requirements:**
- Valid AWS credentials
- Access to an S3 bucket

**Before running:**
1. Open the script
2. Update AWS credentials
3. Update bucket name and prefix to match your S3 location

## General Tips

1. **Virtual Environment**: It's recommended to use a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install pyswmm boto3 requests
   ```

2. **Credentials**: Never commit AWS credentials to version control. Use environment variables in production:
   ```python
   import os
   AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
   AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
   ```

3. **SWMM Models**: The examples assume you have a SWMM model file. You can use any valid .inp file.

4. **Error Handling**: The examples include basic error checking. In production, you'd want more robust error handling.

## Customizing Examples

All examples are designed to be starting points. Feel free to modify them:

- Change weather parameters (ranges, step sizes, etc.)
- Adjust simulation time periods
- Add more observation areas or query points
- Modify SWMM OPTIONS settings
- Use different S3 buckets or prefixes

## Need Help?

- Check the main README: `../README.md`
- Read individual metaagent READMEs in their directories
- Review the metaagent source code for detailed documentation
