"""
Example: Running a SWMM Simulation with Custom Weather

This example demonstrates how to:
1. Generate weather data
2. Interpolate to query points
3. Convert to SWMM format
4. Run a SWMM simulation

Note: You need a valid SWMM .inp file to run this example.
Update the 'network_file' path below to point to your model.
"""

import sys
from pathlib import Path

# Add parent directory to path to import metaagents
sys.path.insert(0, str(Path(__file__).parent.parent))

from metaagents.simulation.weather import metaagent as weather_sim
from metaagents.utilities.weather_interpolation import metaagent as weather_interp
from metaagents.utilities.weather_to_pyswmm import metaagent as weather_converter
from metaagents.simulation.pyswmm import metaagent as pyswmm_sim


def main():
    print("=" * 60)
    print("SWMM Simulation with Custom Weather Example")
    print("=" * 60)

    # IMPORTANT: Update this path to your SWMM model file
    NETWORK_FILE = "path/to/your/model.inp"

    # Optional: AWS credentials for uploading results to S3
    # Leave empty to skip S3 upload
    AWS_ACCESS_KEY_ID = ""
    AWS_SECRET_ACCESS_KEY = ""
    AWS_BUCKET = "xmtwin"

    # Step 1: Initialize weather simulation
    print("\n1. Initializing weather simulation...")
    weather_sim.on_create({
        "use_random_walk": True,
        "precipitation_min": 0.0,
        "precipitation_max": 30.0,
        "precipitation_step": 3.0,
    })

    # Step 2: Generate weather for observation areas
    print("\n2. Generating weather data...")
    weather_result = weather_sim.on_receive({
        "time_delta": 900,  # 15 minutes
        "total_time": 21600,  # 6 hours
        "areas": [
            {"name": "area1", "x": 0.3, "y": 0.7, "precipitation": 5.0, "temperature": 20.0},
            {"name": "area2", "x": 0.7, "y": 0.3, "precipitation": 8.0, "temperature": 21.0}
        ]
    })
    print(f"   Generated {weather_result['num_timesteps']} timesteps")

    # Step 3: Interpolate to rain gauge locations
    print("\n3. Interpolating weather to rain gauges...")
    weather_interp.on_create({})
    interp_result = weather_interp.on_receive({
        "timeseries": {
            "area_timeseries": weather_result['area_timeseries'],
            "start_time": weather_result['start_time'],
            "end_time": weather_result['end_time'],
            "time_delta_seconds": weather_result['time_delta_seconds'],
            "total_time_seconds": weather_result['total_time_seconds'],
            "num_timesteps": weather_result['num_timesteps']
        },
        "query": {
            "rain1": {"x": 0.5, "y": 0.5}  # Update to match your SWMM timeseries names
        }
    })

    # Step 4: Convert to SWMM format
    print("\n4. Converting to SWMM format...")
    weather_converter.on_create({})
    swmm_weather = weather_converter.on_receive({
        "timeseries": interp_result['timeseries'],
        "parameter": "precipitation",
        "start_time": interp_result['start_time'],
        "end_time": interp_result['end_time']
    })

    # Step 5: Initialize SWMM simulation
    print("\n5. Initializing SWMM simulation...")
    swmm_config = {
        "network_file": NETWORK_FILE,
        "source_type": "local"
    }

    # Add AWS credentials if provided
    if AWS_ACCESS_KEY_ID:
        swmm_config.update({
            "aws_access_key_id": AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
            "bucket": AWS_BUCKET
        })

    init_result = pyswmm_sim.on_create(swmm_config)
    print(f"   Status: {init_result['status']}")
    print(f"   Network file: {init_result['network_file_local']}")
    print(f"   S3 configured: {init_result['s3_configured']}")

    # Step 6: Run simulation with weather modifications
    print("\n6. Running SWMM simulation...")
    print("   (This may take a few minutes depending on model size...)")

    sim_result = pyswmm_sim.on_receive({
        "modifications": swmm_weather['modifications']
    })

    print(f"   Status: {sim_result['status']}")
    print(f"   Run ID: {sim_result['run_id']}")

    if sim_result.get('rpt_s3_path'):
        print(f"   Report available at: {sim_result['rpt_s3_path']}")
    else:
        print("   Results not uploaded to S3 (no credentials provided)")

    # Cleanup
    print("\n7. Cleaning up...")
    weather_sim.on_destroy()
    weather_interp.on_destroy()
    weather_converter.on_destroy()
    pyswmm_sim.on_destroy()

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
