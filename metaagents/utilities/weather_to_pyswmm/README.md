# Weather to PySWMM Converter MetaAgent

Converts weather timeseries data into the specific format required by SWMM (Storm Water Management Model).

## What Does It Do?

SWMM expects weather data in a very specific format. This metaagent takes weather timeseries from the Weather Simulation or Interpolation metaagent and reformats it to work with SWMM, including:

- Converting timestamps from ISO format to SWMM format (MM/DD/YYYY HH:MM:SS)
- Extracting specific weather parameters (like precipitation)
- Automatically calculating simulation start/end dates based on current time
- Formatting data lines exactly as SWMM expects

## How to Use

### Step 1: Initialize (on_create)

Simple initialization:

```python
result = on_create({})
```

### Step 2: Convert Weather Data (on_receive)

Provide weather timeseries and specify which parameter to extract:

```python
data = {
    "timeseries": {
        # Output from Weather Interpolation or Simulation
        "rain_gauge_1": {
            "x": 0.5,
            "y": 0.6,
            "columns": ["timestamp", "precipitation", "temperature", ...],
            "timeseries": [
                ("2025-01-01T00:00:00Z", 0.0, 25.0, ...),
                ("2025-01-01T01:00:00Z", 2.5, 24.8, ...),
                # ... more timesteps
            ]
        },
        "rain_gauge_2": { ... }
    },
    "parameter": "precipitation",  # Which weather parameter to extract
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z"
}

result = on_receive(data)
```

**Input Parameters:**
- `timeseries` - Weather data from previous metaagent
- `parameter` - Which weather variable to extract (default: "precipitation")
- `start_time` - Original simulation start time (ISO format)
- `end_time` - Original simulation end time (ISO format)

### Step 3: Use the Output

The output is ready to feed into the PySWMM Simulation metaagent:

```python
{
    "status": "success",
    "modifications": {
        "timeseries": {
            "rain_gauge_1": [
                "01/01/2025  00:00:00     0.00",
                "01/01/2025  01:00:00     2.50",
                "01/01/2025  02:00:00     3.20",
                # ... more lines
            ],
            "rain_gauge_2": [ ... ]
        },
        "options": {
            "start_date": "01/15/2025",
            "start_time": "14:30:00",
            "end_date": "01/16/2025",
            "end_time": "14:30:00"
        }
    }
}
```

## Smart Date Handling

The converter automatically adjusts simulation dates to the current time while preserving the duration:

1. Takes the original start and end times from your weather data
2. Calculates the duration between them
3. Sets the new start time to "now" (current time when converter runs)
4. Sets the new end time to "now + duration"

This ensures your simulation always runs with fresh timestamps, which can be important for some SWMM features.

## SWMM Format Details

SWMM expects timeseries data in this exact format:
```
MM/DD/YYYY  HH:MM:SS     VALUE
```

For example:
```
01/15/2025  14:30:00     5.20
```

- Two spaces between date and time
- Five spaces between time and value
- Values formatted to 2 decimal places by default

## Common Parameters

- `precipitation` - Rainfall in mm/hour (most common)
- `temperature` - Temperature in °C
- `evaporation` - Evaporation rate
- Any other parameter from your weather columns

## Pipeline Position

This metaagent sits between:
- **Input**: Weather Interpolation (or Weather Simulation)
- **Output**: PySWMM Simulation

## Example Workflow

```python
# 1. Generate and interpolate weather
weather_data = weather_interpolation.on_receive({...})

# 2. Convert to SWMM format
swmm_data = weather_to_pyswmm.on_receive({
    "timeseries": weather_data["timeseries"],
    "parameter": "precipitation",
    "start_time": weather_data["start_time"],
    "end_time": weather_data["end_time"]
})

# 3. Run SWMM simulation
simulation_result = pyswmm_simulation.on_receive({
    "modifications": swmm_data["modifications"]
})
```

## Tips

- Make sure your query point names match the timeseries names in your SWMM model
- Common SWMM timeseries names are like "rain1", "RainGauge1", etc.
- If timeseries names don't match, you may need to rename them in your SWMM .inp file or in the query points

## What Gets Modified

The output `modifications` dict contains:

1. **timeseries** - Dictionary mapping timeseries names to formatted data lines
2. **options** - SWMM OPTIONS section updates (start_date, start_time, end_date, end_time)

These modifications are passed directly to the PySWMM Simulation metaagent, which applies them to your SWMM model before running the simulation.
