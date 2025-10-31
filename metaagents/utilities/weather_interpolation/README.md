# Weather Interpolation MetaAgent

Estimates weather conditions at specific points based on data from nearby observation points using Inverse Distance Weighting (IDW).

## What Does It Do?

Think of this as filling in the gaps between weather stations. If you have weather data from a few observation points (areas), this metaagent calculates what the weather would be at any other location you're interested in (query points).

The closer an observation point is to your query point, the more it influences the estimated weather value.

## How to Use

### Step 1: Initialize (on_create)

Simple initialization with no configuration needed:

```python
result = on_create({})
```

### Step 2: Interpolate Weather (on_receive)

Provide observation data (from Weather Simulation) and specify your query points:

```python
data = {
    "timeseries": {
        # Output from Weather Simulation metaagent
        "area_timeseries": {
            "north": {
                "x": 0.2,
                "y": 0.8,
                "columns": ["timestamp", "precipitation", "temperature", ...],
                "timeseries": [(timestamp, values...), ...]
            },
            "south": { ... }
        },
        "start_time": "2025-01-01T00:00:00Z",
        "num_timesteps": 25
    },
    "query": {
        "subcatchment_A": {"x": 0.5, "y": 0.6},
        "subcatchment_B": {"x": 0.3, "y": 0.4},
        "rain_gauge_1": {"x": 0.7, "y": 0.9}
    }
}

result = on_receive(data)
```

**Input Parameters:**
- `timeseries` - Weather data from observation points (typically from Weather Simulation metaagent)
- `query` - Dictionary of named points where you want weather estimates:
  - Key: Name of the query point (e.g., "subcatchment_A")
  - Value: Object with `x` and `y` coordinates (0-1 range)

### Step 3: Use the Output

The output contains interpolated weather for each query point:

```python
{
    "status": "success",
    "timeseries": {
        "subcatchment_A": {
            "x": 0.5,
            "y": 0.6,
            "columns": ["timestamp", "precipitation", "temperature", ...],
            "timeseries": [
                ("2025-01-01T00:00:00Z", 2.3, 24.2, ...),
                # ... more timesteps
            ]
        },
        "subcatchment_B": { ... }
    },
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z",
    "num_timesteps": 25
}
```

## How IDW Works

Inverse Distance Weighting gives more weight to nearby observation points:

1. For each query point, calculate the distance to all observation points
2. Closer points have higher influence (weight = 1 / distance²)
3. Weighted average gives the interpolated value

**Special Cases:**
- If a query point matches an observation point exactly, it uses that observation's value directly
- If a query point is very close (< 0.0000000001) to an observation point, it uses that value

## Tips

- Place observation points (areas) around the edges of your study region
- Use more observation points for better accuracy
- Query point coordinates must use the same coordinate system as your observation points
- All coordinates should be normalized (0-1 range)

## Common Use Cases

1. **SWMM Subcatchments** - Estimate rainfall for each subcatchment based on nearby weather stations
2. **Rain Gauges** - Interpolate to match specific gauge locations in your model
3. **Grid Points** - Create a regular grid of weather estimates

## Pipeline Position

This metaagent sits between:
- **Input**: Weather Simulation (provides observation point data)
- **Output**: Weather to PySWMM (consumes interpolated data)

## Example Workflow

```python
# 1. Generate weather at 3 observation areas
weather_result = weather_simulation.on_receive({
    "time_delta": 3600,
    "total_time": 86400,
    "areas": [
        {"name": "station_1", "x": 0.1, "y": 0.1},
        {"name": "station_2", "x": 0.9, "y": 0.1},
        {"name": "station_3", "x": 0.5, "y": 0.9}
    ]
})

# 2. Interpolate to 5 subcatchment locations
interp_result = weather_interpolation.on_receive({
    "timeseries": weather_result,
    "query": {
        "sub1": {"x": 0.3, "y": 0.3},
        "sub2": {"x": 0.7, "y": 0.3},
        "sub3": {"x": 0.5, "y": 0.5},
        "sub4": {"x": 0.3, "y": 0.7},
        "sub5": {"x": 0.7, "y": 0.7}
    }
})

# 3. Convert to SWMM format
swmm_data = weather_to_pyswmm.on_receive(interp_result)
```

## Technical Details

- **Interpolation Method**: Inverse Distance Weighting (IDW)
- **Power Parameter**: 2.0 (standard IDW, gives quadratic falloff with distance)
- **Distance Metric**: Euclidean distance in 2D
- **Coordinate System**: Normalized (0-1) for both X and Y axes
