"""
Example: Complete Weather Generation and Interpolation Pipeline

This example demonstrates how to:
1. Generate weather data for observation areas
2. Interpolate weather to specific query points
3. View the results

No SWMM simulation is run in this example.
"""

import sys
from pathlib import Path

# Add parent directory to path to import metaagents
sys.path.insert(0, str(Path(__file__).parent.parent))

from metaagents.simulation.weather import metaagent as weather_sim
from metaagents.utilities.weather_interpolation import metaagent as weather_interp


def main():
    print("=" * 60)
    print("Weather Generation and Interpolation Pipeline Example")
    print("=" * 60)

    # Step 1: Initialize weather simulation
    print("\n1. Initializing weather simulation...")
    weather_config = {
        "use_random_walk": True,
        "precipitation_min": 0.0,
        "precipitation_max": 50.0,
        "precipitation_step": 2.0,
        "temperature_min": 10.0,
        "temperature_max": 35.0,
        "temperature_step": 0.5,
    }

    result = weather_sim.on_create(weather_config)
    print(f"   Status: {result['status']}")
    print(f"   Random walk enabled: {result['use_random_walk']}")

    # Step 2: Generate weather for 3 observation areas
    print("\n2. Generating weather data for 3 observation areas...")
    weather_data = {
        "time_delta": 3600,  # 1 hour
        "total_time": 86400,  # 24 hours
        "areas": [
            {
                "name": "north_station",
                "x": 0.2,
                "y": 0.8,
                "precipitation": 0.0,
                "temperature": 25.0,
                "humidity": 60.0
            },
            {
                "name": "south_station",
                "x": 0.8,
                "y": 0.2,
                "precipitation": 2.0,
                "temperature": 27.0,
                "humidity": 55.0
            },
            {
                "name": "center_station",
                "x": 0.5,
                "y": 0.5,
                "precipitation": 1.0,
                "temperature": 26.0,
                "humidity": 58.0
            }
        ]
    }

    weather_result = weather_sim.on_receive(weather_data)
    print(f"   Status: {weather_result['status']}")
    print(f"   Generated {weather_result['num_timesteps']} timesteps")
    print(f"   Time range: {weather_result['start_time']} to {weather_result['end_time']}")

    # Step 3: Initialize interpolation
    print("\n3. Initializing weather interpolation...")
    interp_result = weather_interp.on_create({})
    print(f"   Status: {interp_result['status']}")

    # Step 4: Interpolate to 5 query points (e.g., subcatchments)
    print("\n4. Interpolating weather to 5 query points...")
    interp_data = {
        "timeseries": {
            "area_timeseries": weather_result['area_timeseries'],
            "start_time": weather_result['start_time'],
            "end_time": weather_result['end_time'],
            "time_delta_seconds": weather_result['time_delta_seconds'],
            "total_time_seconds": weather_result['total_time_seconds'],
            "num_timesteps": weather_result['num_timesteps']
        },
        "query": {
            "subcatchment_A": {"x": 0.3, "y": 0.6},
            "subcatchment_B": {"x": 0.7, "y": 0.6},
            "subcatchment_C": {"x": 0.5, "y": 0.5},
            "subcatchment_D": {"x": 0.3, "y": 0.3},
            "subcatchment_E": {"x": 0.7, "y": 0.3}
        }
    }

    interp_result = weather_interp.on_receive(interp_data)
    print(f"   Status: {interp_result['status']}")
    print(f"   Interpolated weather for {len(interp_result['timeseries'])} query points")

    # Step 5: Display sample results
    print("\n5. Sample Results:")
    print("-" * 60)

    # Show first 3 timesteps for each query point
    for query_name, query_data in list(interp_result['timeseries'].items())[:2]:
        print(f"\n   {query_name} (x={query_data['x']}, y={query_data['y']}):")
        print(f"   Columns: {', '.join(query_data['columns'])}")
        print("   First 3 timesteps:")

        for i, timestep in enumerate(query_data['timeseries'][:3]):
            timestamp, precip, temp, pressure, humidity, wind_spd, wind_dir = timestep
            print(f"      {timestamp}: precip={precip:.2f}mm/h, temp={temp:.1f}°C, humidity={humidity:.1f}%")

    # Cleanup
    print("\n6. Cleaning up...")
    weather_sim.on_destroy()
    weather_interp.on_destroy()

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
