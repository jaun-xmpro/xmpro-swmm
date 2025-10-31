# XMPro SWMM MetaAgents

A collection of MetaAgents for running SWMM (Storm Water Management Model) simulations with dynamic weather data in the XMPro DataStreams platform.

## What Are These MetaAgents?

These MetaAgents work together to simulate stormwater systems. They handle everything from generating weather data to running hydraulic simulations and storing results in the cloud.

## MetaAgents Overview

### Simulation MetaAgents

- **PySWMM Simulation** - Runs SWMM hydraulic simulations with customizable parameters and uploads results to S3
- **Weather Simulation** - Creates synthetic weather data (rainfall, temperature, wind, etc.) for multiple locations

### Utility MetaAgents

- **Weather Interpolation** - Estimates weather conditions at specific points based on nearby weather stations
- **Weather to PySWMM Converter** - Translates weather data into the format SWMM expects

### AWS MetaAgents

- **S3 File Access** - Reads and lists files stored in AWS S3 buckets

## Quick Start

### Installation

1. Install Python dependencies:
```bash
pip install pyswmm boto3 requests
```

2. Prepare a SWMM model file (`.inp` format)

3. Configure AWS credentials (if using S3 features)

### Basic Workflow

Here's a typical workflow using these MetaAgents together:

1. **Generate Weather Data** - Use the Weather Simulation metaagent to create weather timeseries for different areas
2. **Interpolate to Points** - Use Weather Interpolation to estimate weather at specific locations in your model
3. **Convert Format** - Use Weather to PySWMM to convert the data into SWMM-compatible format
4. **Run Simulation** - Use PySWMM Simulation to run the hydraulic model with your weather data
5. **Access Results** - Retrieve simulation results from S3 using the S3 File Access metaagent

### Example Scripts

Check the `examples/` directory for complete working examples:

- `example_weather_pipeline.py` - Complete weather generation and interpolation workflow
- `example_swmm_simulation.py` - Running a SWMM simulation with custom weather
- `example_s3_access.py` - Reading files from S3

## Documentation

Each metaagent has its own README with detailed documentation:

- [Weather Simulation](metaagents/simulation/weather/README.md)
- [Weather Interpolation](metaagents/utilities/weather_interpolation/README.md)
- [Weather to PySWMM](metaagents/utilities/weather_to_pyswmm/README.md)
- [PySWMM Simulation](metaagents/simulation/pyswmm/README.md)
- [S3 File Access](metaagents/aws/s3/file_access/README.md)

## MetaAgent Interface

All metaagents follow the XMPro DataStreams MetaAgent pattern with three main functions:

- `on_create(data)` - Initialize the metaagent with configuration
- `on_receive(data)` - Process incoming data and perform the main operation
- `on_destroy(data)` - Clean up resources when done

## Requirements

- Python 3.7+
- pyswmm
- boto3 (for S3 features)
- requests (for HTTP downloads)

## Author

Jaun van Heerden, 2025

## License

See LICENSE file for details.
