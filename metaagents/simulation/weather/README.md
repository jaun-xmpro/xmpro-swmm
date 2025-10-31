# Weather Simulation MetaAgent

Generates synthetic weather data for multiple geographic areas over a specified time period.

## What Does It Do?

This metaagent creates realistic weather timeseries data including:
- Rainfall (mm/hour)
- Temperature (°C)
- Atmospheric pressure (hPa)
- Humidity (%)
- Wind speed (m/s)
- Wind direction (degrees)

You can generate weather for multiple locations (areas) at once, with each area having its own starting conditions and optional weather ranges.

## How to Use

### Step 1: Initialize (on_create)

Set up default weather ranges that apply to all areas:

```python
config = {
    "use_random_walk": True,
    "precipitation_min": 0.0,
    "precipitation_max": 50.0,
    "precipitation_step": 2.0,
    "temperature_min": -10.0,
    "temperature_max": 40.0,
    "temperature_step": 0.5,
    # ... other weather parameter ranges
}

result = on_create(config)
```

**Key Parameters:**
- `use_random_walk` - If True, weather values change gradually over time. If False, weather stays constant.
- `*_min` / `*_max` - Minimum and maximum allowed values for each weather parameter
- `*_step` - How much the value can change per timestep (larger = more variable weather)

### Step 2: Generate Weather (on_receive)

Specify your time range and areas:

```python
data = {
    "start_time": "2025-01-01T00:00:00Z",  # Optional, defaults to now
    "time_delta": 3600,  # Seconds between timesteps (3600 = 1 hour)
    "total_time": 86400,  # Total duration in seconds (86400 = 24 hours)
    "areas": [
        {
            "name": "north",
            "x": 0.2,
            "y": 0.8,
            "precipitation": 0.0,
            "temperature": 25.0,
            "humidity": 60.0
            # ... other starting values
        },
        {
            "name": "south",
            "x": 0.8,
            "y": 0.2,
            "precipitation": 5.0,
            "temperature": 22.0
        }
    ]
}

result = on_receive(data)
```

**Input Parameters:**
- `start_time` - When the simulation starts (ISO format). Optional, defaults to current time.
- `time_delta` - Seconds between each data point
- `total_time` - Total simulation duration in seconds
- `areas` - List of geographic areas, each with:
  - `name` - Unique identifier
  - `x`, `y` - Normalized coordinates (0-1 range)
  - Starting values for weather parameters (optional)
  - `weather_ranges` - Override default ranges for this specific area (optional)

### Step 3: Use the Output

The output contains timeseries data for each area:

```python
{
    "status": "success",
    "area_timeseries": {
        "north": {
            "x": 0.2,
            "y": 0.8,
            "columns": ["timestamp", "precipitation", "temperature", ...],
            "timeseries": [
                ("2025-01-01T00:00:00Z", 0.0, 25.0, 1013.25, 60.0, 0.0, 0.0),
                ("2025-01-01T01:00:00Z", 1.2, 24.8, 1013.5, 61.5, 0.5, 45.0),
                # ... more timesteps
            ]
        },
        "south": { ... }
    },
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z",
    "num_timesteps": 25
}
```

## Random Walk vs. Static Weather

- **Static** (`use_random_walk=False`): Weather values stay constant at the starting values
- **Random Walk** (`use_random_walk=True`): Weather values change gradually, staying within the defined ranges. Good for realistic weather patterns.

## Tips

- Use smaller `*_step` values for smoother, more gradual weather changes
- Coordinates (`x`, `y`) should be between 0 and 1. They're used by the interpolation metaagent later.
- Each area can have different starting conditions to simulate spatial variation

## Common Use Cases

1. **Uniform Weather** - Use one area with static values for simple scenarios
2. **Spatial Variation** - Use multiple areas with different starting values
3. **Dynamic Weather** - Enable random walk for realistic changing conditions
4. **Storm Events** - Start with high precipitation values in certain areas

## Output Format

Data is organized by area, with each area containing:
- Location coordinates (x, y)
- Column names describing the data fields
- Timeseries as a list of tuples (timestamp, values...)

This format feeds directly into the Weather Interpolation metaagent.
